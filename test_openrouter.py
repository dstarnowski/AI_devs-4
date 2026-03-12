from my_openrouter import MyOpenrouter
import sekrets

ai = MyOpenrouter(sekrets.openrouter_key)

answer = ai.chat(
    messages=[{"role": "user", "content": "What is the capital of Poland? Answer in one sentence."}],
    label="test-run",
)
print(f"\nAnswer: {answer}")

answer = ai.chat(
    messages=[{"role": "user", "content": "What is the capital of Germany? Answer with just the name of the city."}],
    label="test-run-2",
)
print(f"\nAnswer: {answer}")

print(f"\nSession stats: {ai.get_session_stats()}")
