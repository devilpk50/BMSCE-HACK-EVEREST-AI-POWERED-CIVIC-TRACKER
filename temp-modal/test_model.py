import time
from model_service import CivicAI

def run_test(img_path):
    print(f"--- Testing Image: {img_path} ---")
    ai = CivicAI()
    
    start = time.time()
    result = ai.validate_report(img_path)
    end = time.time()
    
    print(f"Status: {'✅ Verified' if result['is_valid'] else '❌ Rejected'}")
    print(f"Confidence: {result['confidence']:.2f}")
    print(f"Fingerprint: {result['fingerprint']}")
    print(f"Inference Time: {(end - start) * 1000:.2f}ms")

if __name__ == "__main__":
    # Replace 'sample.jpg' with a real image path in your directory
    # run_test("sample.jpg")
    pass