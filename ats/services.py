from django.db import transaction
from resumes.models import ATSAnalysis, Resume, JobDescription
from ai_engine.services import AIEngine


def compute_keyword_match(resume: Resume, job_desc: JobDescription):
    engine = AIEngine()
    resume_text = ' '.join([resume.summary, resume.title, ' '.join([skill.name for skill in resume.skills.all()])])
    resume_keywords = set(engine.extract_keywords(resume_text))
    jd_keywords = set(engine.extract_keywords(job_desc.description))
    if not jd_keywords:
        return 0.0
    intersection = resume_keywords.intersection(jd_keywords)
    return round(len(intersection) / len(jd_keywords) * 100, 2)


def compute_missing_skills(resume: Resume, job_desc: JobDescription):
    resume_skills = {skill.name.lower() for skill in resume.skills.all()}
    required = {keyword.lower() for keyword in job_desc.extracted_keywords}
    missing = [skill for skill in required if skill not in resume_skills]
    return missing[:10]


def compute_weak_sections(resume: Resume):
    weak = []
    if not resume.summary:
        weak.append('Summary')
    if not resume.experiences.exists():
        weak.append('Experience')
    if not resume.skills.exists():
        weak.append('Skills')
    return weak


def compute_score(resume: Resume, keyword_match: float):
    structure_score = 20 if resume.summary and resume.experiences.exists() and resume.skills.exists() else 10
    match_score = min(max(int(keyword_match), 0), 30)
    readability_score = 20 if len(resume.summary or '') > 50 else 10
    skills_score = 20 if resume.skills.count() >= 6 else 10
    total = structure_score + match_score + readability_score + skills_score
    return min(total, 100)


@transaction.atomic
def score_resume(resume: Resume, job_desc: JobDescription):
    engine = AIEngine()
    engine.analyze_job_description(job_desc)
    keyword_match = compute_keyword_match(resume, job_desc)
    missing_skills = compute_missing_skills(resume, job_desc)
    weak_sections = compute_weak_sections(resume)
    score = compute_score(resume, keyword_match)
    project_impact = engine.analyze_project_impact(resume)
    analysis, _ = ATSAnalysis.objects.update_or_create(
        resume=resume,
        defaults={
            'score': score,
            'keyword_match': keyword_match,
            'missing_keywords': missing_skills,
            'weak_sections': weak_sections,
            'project_impact_analysis': project_impact,
            'suggestions': [
                'Improve section structure',
                'Include more target keywords from the JD',
                'Add measurable accomplishments to experience bullets',
            ],
        },
    )
    return analysis
