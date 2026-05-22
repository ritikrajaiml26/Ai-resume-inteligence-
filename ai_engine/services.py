import os
import re
import json
from django.conf import settings
from resumes.models import Resume, JobDescription, GeneratedResume


def _load_nlp():
    try:
        import spacy
        return spacy.load('en_core_web_sm')
    except Exception:
        return None


def _ensure_nltk():
    try:
        import nltk
        nltk.download('punkt', quiet=True)
    except Exception:
        pass


class AIEngine:
    def __init__(self):
        self.gemini = None
        self.nlp = None
        self.api_key = getattr(settings, 'GEMINI_API_KEY', '')
        _ensure_nltk()

    def _get_gemini(self):
        if self.gemini is not None:
            return self.gemini
        try:
            import google.generativeai as genai
            self.gemini = genai
            if self.api_key:
                self.gemini.configure(api_key=self.api_key)
            return self.gemini
        except ImportError:
            self.gemini = None
            return None

    def _get_nlp(self):
        if self.nlp is not None:
            return self.nlp
        self.nlp = _load_nlp()
        return self.nlp

    def extract_keywords(self, text):
        nlp = self._get_nlp()
        if not nlp:
            return []
        doc = nlp(text.lower())
        keywords = {token.lemma_ for token in doc if token.is_alpha and not token.is_stop and len(token.text) > 2}
        return list(keywords)

    def analyze_job_description(self, job_desc: JobDescription):
        keywords = self.extract_keywords(job_desc.description)
        required = []
        nlp = self._get_nlp()
        if nlp:
            required = [token.text for token in nlp(job_desc.description) if token.like_num or token.ent_type_ == 'ORG']
        job_desc.extracted_keywords = keywords
        job_desc.required_skills = required
        job_desc.save()
        return job_desc

    def improve_summary(self, resume: Resume):
        prompt = (
            f"Rewrite the following professional summary for ATS optimization and modern resume style:\n\n{resume.summary}\n\n"
            "Keep it concise, action-oriented, and focused on technical impact."
        )
        result = self._call_gemini(prompt)
        resume.summary = result.strip()
        resume.save()
        return resume.summary

    def improve_bullet_points(self, resume: Resume):
        experience_bullets = []
        for exp in resume.experiences.all():
            if exp.bullets:
                experience_bullets.append(f"{exp.role} at {exp.company}: {exp.bullets}")
        if not experience_bullets:
            return []
        prompt = (
            "Rewrite these resume bullet points with action verbs, quantifiable language, and ATS-friendly structure:\n"
            + "\n".join(experience_bullets)
        )
        improved = self._call_gemini(prompt)
        bullets = improved.strip().split('\n')
        for exp, bullet in zip(resume.experiences.all(), bullets):
            exp.bullets = bullet
            exp.save()
        return bullets

    def generate_summaries(self, resume: Resume):
        prompts = {
            'professional': f"Write a professional summary for this resume:\n{resume.summary}",
            'role_based': f"Create a role-based introduction for a resume targeting {resume.title}",
            'ats_optimized': f"Write an ATS-optimized resume summary for a candidate with these skills: {', '.join([skill.name for skill in resume.skills.all()])}.",
        }
        results = {}
        for key, prompt in prompts.items():
            results[key] = self._call_gemini(prompt).strip()
        return results

    def analyze_project_impact(self, resume: Resume):
        projects = []
        for proj in resume.projects.all():
            projects.append(f"{proj.title}: {proj.description}")
        if not projects:
            return "No projects found to analyze."
        prompt = (
            "Analyze the impact of these projects for a resume. Evaluate if they show technical depth, "
            "quantifiable results, and clear use of technologies:\n" + "\n".join(projects)
        )
        return self._call_gemini(prompt)

    def optimize_resume(self, resume: Resume, job_desc: JobDescription):
        self.analyze_job_description(job_desc)
        if resume.summary:
            self.improve_summary(resume)
        self.improve_bullet_points(resume)
        ai_summaries = self.generate_summaries(resume)
        self.generate_resume_templates(resume)
        
        # Save version history
        from resumes.models import ResumeVersion
        import json
        ResumeVersion.objects.create(
            resume=resume,
            summary=resume.summary,
            experience_data=[{"role": exp.role, "company": exp.company, "bullets": exp.bullets} for exp in resume.experiences.all()]
        )
        
        return ai_summaries

    def chat_edit_resume(self, resume: Resume, user_message: str):
        resume_data = {
            "full_name": resume.full_name,
            "title": resume.title,
            "summary": resume.summary,
            "skills": [s.name for s in resume.skills.all()],
            "experiences": [{"role": e.role, "company": e.company, "bullets": e.bullets} for e in resume.experiences.all()],
        }
        
        prompt = (
            f"You are an expert AI Resume Editor. The user wants to modify their resume. \n"
            f"User message: '{user_message}' \n"
            f"Current Resume Data: {json.dumps(resume_data)} \n\n"
            f"Task: \n"
            f"1. Determine what changes are needed based on the user's request. \n"
            f"2. Return a valid JSON object with EXACTLY these fields: \n"
            f"   - 'explanation': A friendly message explaining what you changed. \n"
            f"   - 'updates': A dictionary of fields to update (keys: 'full_name', 'title', 'summary'). \n"
            f"   - 'skill_updates': A list of all skills (if changed). \n"
            f"   - 'experience_updates': A list of dictionaries ('role', 'company', 'bullets'). \n\n"
            f"IMPORTANT: Return ONLY the JSON. No markdown, no backticks, no text before or after."
        )
        
        try:
            response_text = self._call_gemini(prompt, json_mode=True).strip()
            # Try to find JSON block if it exists
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group()
                
            return json.loads(response_text)
        except Exception as e:
            return {"explanation": f"AI responded with an invalid format. Please try again or rephrase your request. (Error: {str(e)})", "updates": {}}

    def generate_resume_templates(self, resume: Resume):
        from templates_engine.services import build_template_html
        templates = {}
        for style in ['corporate', 'modern', 'minimal']:
            GeneratedResume.objects.filter(resume=resume, template_style=style).delete()
            html_content = build_template_html(resume, style)
            templates[style] = html_content
            GeneratedResume.objects.create(resume=resume, template_style=style, content_html=html_content)
        return templates

    def _call_gemini(self, prompt, json_mode=False):
        if not self.api_key:
            return 'Gemini API key is not configured. Please add it to your environment.'
        genai = self._get_gemini()
        if not genai:
            return 'Gemini SDK is not available. Please install the google-generativeai package.'
        try:
            model = genai.GenerativeModel('gemini-2.5-flash')
            config = {
                "temperature": 0.7,
                "max_output_tokens": 2000,
            }
            if json_mode:
                config["response_mime_type"] = "application/json"
                
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(**config)
            )
            return response.text
        except Exception as e:
            return f'Unable to call Gemini API. Error: {str(e)}'
