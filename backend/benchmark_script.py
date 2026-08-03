import os
import sys
import json
from dotenv import load_dotenv
from google import genai

# Setup imports correctly for the backend context
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from app.services.parser_service import DocumentStore, generate_questions
from app.services.chunking_engine import chunk_text_dp

# Realistic 1-Page JD
JD_TEXT = """
Senior Distributed Backend Engineer
Requirements:
- 7+ years of professional software engineering experience, with a focus on backend systems.
- Expert-level proficiency in Python, Go, or Java, including deep knowledge of concurrency and memory management.
- Proven track record of designing, building, and operating large-scale distributed systems and microservices architectures in production.
- Deep understanding of database engineering, encompassing both relational (PostgreSQL, MySQL) and NoSQL (Cassandra, MongoDB, DynamoDB) paradigms. Experience with complex data modeling, query optimization, and sharding strategies.
- Hands-on experience with event-driven architectures and message brokering systems such as Apache Kafka, RabbitMQ, or AWS Kinesis.
- Strong DevOps mindset with solid experience in containerization (Docker), orchestration (Kubernetes), and CI/CD pipelines (GitHub Actions, GitLab CI).
- Extensive experience with cloud platforms, preferably AWS (EC2, S3, RDS, EKS, Lambda) or GCP.
- Familiarity with caching strategies (Redis, Memcached) and CDN integration to optimize latency.
- Experience with system observability, monitoring, and alerting (Prometheus, Grafana, DataDog, ELK stack).
Responsibilities:
- Architect and develop highly available, scalable, and fault-tolerant backend services that handle millions of requests per day.
- Conduct rigorous performance profiling and optimization to resolve architectural bottlenecks and reduce latency.
- Lead the technical design process, write comprehensive architecture decision records (ADRs), and conduct thorough code reviews.
- Mentor and elevate junior and mid-level engineers, fostering a culture of technical excellence and best practices.
- Collaborate closely with product managers, frontend engineers, and data scientists to deliver cross-functional initiatives.
"""

# Realistic 2-Page CV
CV_TEXT = """
Alex Chen
Senior Software Engineer | 8 years experience | alex.chen@email.com

Summary:
Results-driven Senior Backend Engineer with 8 years of experience specializing in distributed systems, high-throughput APIs, and cloud infrastructure. Passionate about performance optimization and mentoring engineering teams.

Experience:
TechFlow Inc (Jan 2021 - Present) - Senior Backend Engineer
- Spearheaded the migration of a legacy Ruby on Rails monolith to a Go and gRPC-based microservices architecture, improving system throughput by 300% and reducing average response times from 450ms to 80ms.
- Designed and implemented a real-time event processing pipeline using Apache Kafka and Apache Flink, capable of ingesting and analyzing 50,000 events per second for fraud detection.
- Architected a distributed caching layer using Redis Cluster, significantly reducing database load and improving API latency during peak traffic events (Black Friday).
- Led a squad of 4 engineers, conducting weekly architecture syncs, code reviews, and pair programming sessions.
- Managed a highly available PostgreSQL database cluster (10TB+ data), implementing table partitioning, connection pooling (PgBouncer), and automated failover mechanisms.
- Championed the adoption of Kubernetes (AWS EKS) for container orchestration, creating Helm charts and integrating with DataDog for comprehensive observability.

CloudNet Solutions (Mar 2017 - Dec 2020) - Software Engineer
- Developed scalable RESTful APIs in Python (FastAPI/Django) to support an internal analytics dashboard used by 500+ employees.
- Optimized slow SQL queries and redesigned database schemas in MySQL, resulting in a 60% reduction in report generation time.
- Implemented a CI/CD pipeline using Jenkins and Docker, reducing deployment time from 2 hours to 15 minutes and eliminating manual deployment errors.
- Integrated third-party payment gateways (Stripe, PayPal) ensuring PCI-DSS compliance and secure transaction handling.
- Wrote extensive unit and integration tests (PyTest), maintaining a code coverage of over 90%.

Innova Startup (Jun 2015 - Feb 2017) - Junior Developer
- Built internal tooling and automated cron jobs using Python scripts.
- Maintained legacy PHP applications and assisted in minor bug fixes.
"""

def generate_naive_questions(client: genai.Client) -> list[str]:
    prompt = f"""
    You are an expert technical interviewer.
    Given the following Job Description (JD) and candidate Resume (CV), generate 5 highly specific, deep, and challenging interview questions.
    
    JD:
    {JD_TEXT}
    
    CV:
    {CV_TEXT}
    
    Return the output strictly as a JSON array of 5 strings. No other text or markdown.
    """
    response = client.models.generate_content(
        model='gemini-3.7-flash',
        contents=prompt
    )
    import re
    raw_text = response.text.strip()
    match = re.search(r'\[.*\]', raw_text, re.DOTALL)
    if match:
        return json.loads(match.group(0))
    return json.loads(raw_text)


def run_benchmark():
    api_key = os.environ.get("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)

    print("Generating questions using Naive Approach (Direct Prompting)...")
    naive_questions = generate_naive_questions(client)
    
    print("Generating questions using Viva-Verse Approach (DP Chunking + K-Means)...")
    store = DocumentStore()
    
    # We create pseudo pages
    pages = [{"page": 1, "text": f"Job Description:\n{JD_TEXT}\n\nResume:\n{CV_TEXT}"}]
    
    # Use chunk_text_dp directly with a lower token limit to simulate 
    # a dense multi-page resume being chunked semantically
    chunks, labels = chunk_text_dp(pages, max_tokens_per_chunk=150) 
    store.add_chunks(chunks, labels)
    
    # Ensure exactly 5 clusters/questions are generated
    viva_questions = generate_questions(store, num=5)
    viva_questions_text = [q['question'] for q in viva_questions]

    print("Running LLM-as-a-Judge Evaluation...")
    judge_prompt = f"""
    You are an impartial expert technical interviewer evaluating two sets of interview questions generated by AI systems.
    
    Context:
    JD: {JD_TEXT}
    CV: {CV_TEXT}
    
    Question Set A (Naive AI):
    {json.dumps(naive_questions, indent=2)}
    
    Question Set B (Viva-Verse DP Chunking + SBERT + K-Means):
    {json.dumps(viva_questions_text, indent=2)}
    
    Evaluate the two sets out of 10 for the following criteria:
    1. JD/CV Specificity & Depth (Are the questions tied strictly to the candidate's actual experience and probing deep architectural trade-offs?)
    2. Topic Distribution / Anti-Hyperfixation (Did the approach cover the ENTIRE resume—e.g. asking about both their recent Kafka/Microservices experience AND their older CI/CD, Testing, or Leadership experience? Or did it lazily hyper-fixate on just the top 2 bullets?)
    
    Output a strictly formatted Markdown report analyzing both approaches. Focus heavily on how well the approach forced semantic diversity across the entire 8-year timeline of the candidate. Finally, give a verdict on which approach is structurally superior for a comprehensive 360-degree interview.
    Do not use markdown code blocks like ```markdown, just output raw markdown.
    """
    
    eval_response = client.models.generate_content(
        model='gemini-3.7-flash',
        contents=judge_prompt
    )
    
    report = eval_response.text
    
    output_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'benchmark_results.md')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("# Viva-Verse Generative Pipeline Benchmark\n\n")
        f.write("## Approach A (Naive LLM)\n")
        for q in naive_questions:
            f.write(f"- {q}\n")
        f.write("\n## Approach B (DP Chunking + K-Means Clustering)\n")
        for q in viva_questions_text:
            f.write(f"- {q}\n")
        f.write("\n## Judge Evaluation\n")
        f.write(report)
        
    print(f"Benchmark complete. Results saved to {output_path}")

if __name__ == "__main__":
    run_benchmark()
