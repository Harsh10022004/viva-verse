import re
import json

def _extract_failed_skills_from_report(report_text: str):
    failed_skills = []
    weakness_patterns = [
        r"(?i)(deficit|vulnerabilit|weakness|gap|improve|lacking|weak|critical area|action item).*?(?=###|\Z)",
    ]

    weakness_sections = []
    for pat in weakness_patterns:
        matches = re.findall(pat, report_text, re.DOTALL)
        weakness_sections.extend(matches)
        
    print("Weakness sections extracted:", weakness_sections)

    with open('c:\\Users\\ASUS\\Desktop\\BITS_CAP_101\\backend\\app\\utils\\skill_metadata.json') as f:
        skill_db = json.load(f)

    report_lower = report_text.lower()
    for skill_name in skill_db:
        pattern = r"\b" + re.escape(skill_name.lower()) + r"\b"
        if re.search(pattern, report_lower):
            for match in re.finditer(pattern, report_lower):
                start = max(0, match.start() - 200)
                end = min(len(report_lower), match.end() + 200)
                context = report_lower[start:end]
                negative_words = ["weak", "gap", "deficit", "improve", "lack", "miss",
                                  "insufficient", "fail", "poor", "below", "struggle",
                                  "needs work", "remediat", "vulnerab", "critical"]
                if any(nw in context for nw in negative_words):
                    if skill_name not in failed_skills:
                        failed_skills.append(skill_name)
                    break

    return failed_skills[:15]

def extract_questions(report):
    per_question = []
    q_pattern = r"\|\s*\*?Q?(\d+)\*?\s*\|\s*([^|]+?)\s*\|\s*\*?(\d+)\*?(?:\s*/\s*10)?\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|"
    for match in re.finditer(q_pattern, report):
        per_question.append(match.group(1))
    return per_question

with open('C:\\Users\\ASUS\\.gemini\\antigravity-ide\\brain\\14751480-b318-44bc-b6ea-c5ffc5a3229e\\simulated_dashboard_output.md', encoding='utf-8') as f:
    text = f.read()
    
print("Failed Skills:", _extract_failed_skills_from_report(text))
print("Questions:", extract_questions(text))
