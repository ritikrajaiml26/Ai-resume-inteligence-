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
        self.client = None
        self.nlp = None
        self.api_key = getattr(settings, 'GROQ_API_KEY', '')
        _ensure_nltk()

    def _get_client(self):
        """Groq client lazily initialize karta hai (OpenAI-compatible API)."""
        if self.client is not None:
            return self.client
        try:
            from openai import OpenAI
            if not self.api_key:
                return None
            # Groq uses OpenAI-compatible API — sirf base_url change hota hai
            self.client = OpenAI(
                api_key=self.api_key,
                base_url="https://api.groq.com/openai/v1"
            )
            return self.client
        except ImportError:
            self.client = None
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
            "Keep it concise, action-oriented, and focused on technical impact. Return only the improved summary text."
        )
        result = self._call_groq(prompt)
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
            "Rewrite these resume bullet points with strong action verbs, quantifiable language, and ATS-friendly structure. "
            "Return each bullet on a new line:\n"
            + "\n".join(experience_bullets)
        )
        improved = self._call_groq(prompt)
        bullets = improved.strip().split('\n')
        for exp, bullet in zip(resume.experiences.all(), bullets):
            exp.bullets = bullet
            exp.save()
        return bullets

    def generate_summaries(self, resume: Resume):
        skill_names = ', '.join([skill.name for skill in resume.skills.all()])
        projects = '; '.join([f"{p.name}: {p.description}" for p in resume.projects.all()])
        experiences = '; '.join([f"{e.role} at {e.company}: {e.description}" for e in resume.experiences.all()])

        prompt = (
            f"Generate a professional, ATS-optimized resume summary of exactly 50 words for {resume.full_name or 'the candidate'}.\n"
            f"Target Role/Title: {resume.title}\n"
            f"Skills: {skill_names or 'Not specified'}\n"
            f"Projects: {projects or 'None'}\n"
            f"Experience: {experiences or 'None'}\n\n"
            f"Instructions:\n"
            f"1. Write a professional, high-impact summary of around 45 to 55 words.\n"
            f"2. Focus on the candidate's skills and projects to show high technical competence.\n"
            f"3. Return ONLY the summary text, no explanations, no headers, no intro, no markdown."
        )

        summary = self._call_groq(prompt).strip()
        # Clean any potential quotes or markdown
        summary = re.sub(r'^["\'`]+|["\'`]+$', '', summary).strip()

        return {
            'professional': summary,
            'role_based': summary,
            'ats_optimized': summary
        }

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
        return self._call_groq(prompt)

    def optimize_resume(self, resume: Resume, job_desc: JobDescription):
        self.analyze_job_description(job_desc)
        if resume.summary:
            self.improve_summary(resume)
        self.improve_bullet_points(resume)
        ai_summaries = self.generate_summaries(resume)
        self.generate_resume_templates(resume)

        # Save version history
        from resumes.models import ResumeVersion
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

        system_prompt = (
            "You are an expert AI Resume Editor. Your task is to analyze the user's request "
            "and return a valid JSON object with EXACTLY these fields:\n"
            "  - 'explanation': A friendly message explaining what you changed.\n"
            "  - 'updates': A dictionary of fields to update (keys: 'full_name', 'title', 'summary').\n"
            "  - 'skill_updates': A list of all skills (if changed).\n"
            "  - 'experience_updates': A list of dictionaries ('role', 'company', 'bullets').\n"
            "IMPORTANT: Return ONLY valid JSON. No markdown, no backticks, no extra text."
        )

        user_prompt = (
            f"User request: '{user_message}'\n\n"
            f"Current Resume Data:\n{json.dumps(resume_data, indent=2)}"
        )

        try:
            response_text = self._call_groq(user_prompt, system=system_prompt, json_mode=True).strip()
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group()
            return json.loads(response_text)
        except Exception as e:
            return {
                "explanation": f"AI responded with an invalid format. Please try again. (Error: {str(e)})",
                "updates": {}
            }

    def generate_resume_templates(self, resume: Resume):
        from templates_engine.services import build_template_html
        templates = {}
        for style in ['corporate', 'modern', 'minimal']:
            GeneratedResume.objects.filter(resume=resume, template_style=style).delete()
            html_content = build_template_html(resume, style)
            templates[style] = html_content
            GeneratedResume.objects.create(resume=resume, template_style=style, content_html=html_content)
        return templates

    def _call_groq(self, prompt: str, system: str = None, json_mode: bool = False) -> str:
        """
        Groq API ko call karta hai — Free, Fast, OpenAI-compatible.
        Model: llama-3.3-70b-versatile (best free model for resume writing)
        """
        if not self.api_key:
            return 'Groq API key configure nahi hai. Please .env mein GROQ_API_KEY add karein.'

        client = self._get_client()
        if not client:
            return 'OpenAI package available nahi hai. Please `pip install openai` run karein.'

        try:
            messages = []

            # System message
            if system:
                messages.append({"role": "system", "content": system})
            else:
                messages.append({
                    "role": "system",
                    "content": (
                        "You are an expert AI Resume Writer and Career Coach. "
                        "You help users create professional, ATS-optimized resumes "
                        "with clear, impactful language and strong action verbs. "
                        "Always be concise, professional, and results-oriented."
                    )
                })

            messages.append({"role": "user", "content": prompt})

            kwargs = {
                "model": "llama-3.3-70b-versatile",  # Best free model on Groq
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 2000,
            }

            # JSON mode — Groq supports this too
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}

            response = client.chat.completions.create(**kwargs)
            return response.choices[0].message.content

        except Exception as e:
            return f'Groq API call failed. Error: {str(e)}'
