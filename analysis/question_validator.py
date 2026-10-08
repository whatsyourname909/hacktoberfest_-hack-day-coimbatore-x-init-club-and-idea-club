import os
import json
import concurrent.futures
from models.schemas import QuestionValidation
from agents.llm import structured_call

def validate_question_local(question: str, dataset_info: dict) -> dict:
    """Reject only questions that are clearly unusable.

    Real questions are short and varied ("Was this decline seasonal?",
    "Which departments had the highest attrition?"), so this check stays
    lenient. Whether a question fits the data is decided later, when the
    question is parsed against the dataset's actual columns and months.

    Returns:
        {"valid": bool, "reason": str | None}
    """
    words = [word.strip("?.,!:;\"'") for word in question.split()]
    words = [word for word in words if word]
    if len(words) < 3:
        return {"valid": False, "reason": "Please ask a full question, for example: \"Why did revenue fall in March?\""}
    if not any(any(ch.isalpha() for ch in word) for word in words):
        return {"valid": False, "reason": "The question needs words, not just numbers or symbols."}
    return {"valid": True, "reason": None}

def validate_question_ai(question: str, dataset_info: dict) -> dict:
    """Use Gemma to check if a question is answerable from the dataset.
    
    Returns:
        {"valid": bool, "reason": str | None, "rephrased": str | None}
    """
    if not os.getenv("GEMMA_API_KEY"):
        return {"valid": True, "reason": None, "rephrased": None}
        
    prompt = f"""
Given the following dataset schema:
{json.dumps(dataset_info, default=str)}

Is the following question answerable from the available data?
Question: {question}

If not, explain why briefly.
If it's close but imprecise, suggest a rephrased version.
"""
    try:
        def run_ai():
            return structured_call(QuestionValidation, prompt)
            
        # Don't use the executor as a context manager: its exit waits for the call
        # to finish, which would make the 5-second limit meaningless.
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        try:
            future = executor.submit(run_ai)
            result = future.result(timeout=5.0)
        finally:
            executor.shutdown(wait=False)
            
        if result:
            return {
                "valid": result.is_valid, 
                "reason": result.reason,
                "rephrased": result.rephrased_question
            }
        return {"valid": True, "reason": None, "rephrased": None}
    except Exception as e:
        print(f"AI validation failed or timed out: {e}")
        return {"valid": True, "reason": None, "rephrased": None}
