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

    def parse_resume_text(self, text: str):
        """Uses AI to parse raw extracted resume text into structured JSON format."""
        system_prompt = (
            "You are an expert AI Resume Parser. Your task is to extract details from the raw resume text "
            "and format them into a valid JSON object. Do not invent any information, extract what is available.\n"
            "If any field is missing or not found in the text, return an empty string or empty list as appropriate.\n\n"
            "JSON structure to return:\n"
            "Return a valid JSON object with EXACTLY these fields:\n"
            "  - 'full_name': Candidate's full name\n"
            "  - 'title': Target role/title\n"
            "  - 'summary': A summary statement (around 50-100 words)\n"
            "  - 'contact_email': Email address\n"
            "  - 'contact_phone': Phone number\n"
            "  - 'skills': List of skill names (e.g. ['Python', 'Django', 'React'])\n"
            "  - 'experiences': List of dictionaries with keys ('role', 'company', 'duration', 'location', 'description')\n"
            "  - 'projects': List of dictionaries with keys ('name', 'technologies', 'description')\n\n"
            "IMPORTANT: Return ONLY valid JSON. No markdown, no backticks, no extra text."
        )
        
        user_prompt = f"Raw Resume Text:\n{text}"
        try:
            response_text = self._call_groq(user_prompt, system=system_prompt, json_mode=True).strip()
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group()
            return json.loads(response_text)
        except Exception as e:
            print(f"Error parsing resume text: {e}")
            return {}

    def chat_edit_resume(self, resume: Resume, user_message: str, user_name: str = None, job_desc: str = "", missing_skills: list = None):
        resume_data = {
            "full_name": resume.full_name,
            "title": resume.title,
            "summary": resume.summary,
            "skills": [s.name for s in resume.skills.all()],
            "experiences": [{"role": e.role, "company": e.company, "bullets": e.bullets} for e in resume.experiences.all()],
        }

        greeting_name = user_name if user_name else (resume.full_name or "Candidate")
        skills_str = ", ".join(missing_skills) if missing_skills else "none"

        system_prompt = (
            "You are an expert AI Resume Editor. Your task is to analyze the user's request, "
            "determine what changes are needed, apply them, and respond in a very friendly, "
            f"conversational way in Hinglish (Hindi + English mix) or English. Always greet the user as '{greeting_name}' at the beginning.\n\n"
            "Context Information:\n"
            f"- Mismatched/Missing Skills for this job: {skills_str}\n"
            f"- Target Job Description: {job_desc}\n\n"
            "Special Directives:\n"
            "- ALWAYS mention the mismatched/missing skills in your response. Point out which skills are currently missing from their resume and advise adding them.\n"
            "- If the user says 'tum add kr do', 'add them', 'add it', 'optimize', 'tum kr do', or similar requests:\n"
            "  1. You MUST automatically inject all missing skills into 'skill_updates'.\n"
            "  2. Rewrite their 'summary' to be highly professional and incorporate these skills (around 50 words).\n"
            "  3. Rewrite/enhance the experience bullets to naturally showcase these newly added skills. Make it extremely ATS-optimized!\n"
            "  4. Confirm this in your friendly Hinglish explanation (e.g. 'Maine aapke resume me saare missing skills add kar diye hain aur resume fully optimize kar diya hai!').\n"
            f"- Always keep your 'explanation' friendly, welcoming, and natural. Greet the user by saying 'Namaste {greeting_name}!' or similar.\n"
            "- At the end of the 'explanation' message, ALWAYS ask:\n"
            "  'Maine aapka resume update kar diya hai! Kya aap isme kuch aur change karwana chahte hain?'\n"
            "  (or in English: 'I have updated your resume! Would you like me to make any other changes?').\n\n"
            "JSON structure to return:\n"
            "Return a valid JSON object with EXACTLY these fields:\n"
            "  - 'explanation': Friendly chat message pointing out missing skills, explaining changes, and asking what else to do.\n"
            "  - 'updates': Dictionary of field updates (keys: 'full_name', 'title', 'summary'). Only include changed fields.\n"
            "  - 'skill_updates': List of all skills (if changed/updated).\n"
            "  - 'experience_updates': List of dictionaries ('role', 'company', 'bullets' for description).\n\n"
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
