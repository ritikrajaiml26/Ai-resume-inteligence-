import io
import os
import json
import tempfile

try:
    import pypdf
except ImportError:
    pypdf = None

try:
    import docx
except ImportError:
    docx = None
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from .forms import ResumeForm, ManualResumeForm, JobDescriptionForm
from .models import Resume, JobDescription, GeneratedResume, Skill, Education, Experience, Project, Certification, Achievement
from ai_engine.services import AIEngine
from ats.services import score_resume
from templates_engine.services import build_template_html


def extract_text_from_file(file_obj):
    filename = file_obj.name.lower()
    text = ""
    try:
        if filename.endswith('.pdf'):
            if pypdf is None:
                raise ImportError("pypdf is not installed in the environment.")
            reader = pypdf.PdfReader(file_obj)
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    text += t + "\n"
        elif filename.endswith('.docx'):
            if docx is None:
                raise ImportError("python-docx is not installed in the environment.")
            doc = docx.Document(file_obj)
            for para in doc.paragraphs:
                text += para.text + "\n"
        else:
            text = file_obj.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"Error extracting text from file: {e}")
        try:
            file_obj.seek(0)
            text = file_obj.read().decode('utf-8', errors='ignore')
        except:
            pass
    return text



def parse_manual_fields(resume, form):
    """Parse raw text fields into related model objects."""
    Skill.objects.filter(resume=resume).delete()
    Education.objects.filter(resume=resume).delete()
    Experience.objects.filter(resume=resume).delete()
    Project.objects.filter(resume=resume).delete()
    Certification.objects.filter(resume=resume).delete()
    Achievement.objects.filter(resume=resume).delete()

    # Skills: comma-separated
    skills_raw = form.cleaned_data.get('skills_raw', '')
    for name in [item.strip() for item in skills_raw.split(',') if item.strip()]:
        Skill.objects.create(resume=resume, name=name)

    # Education: Degree | Institution | Year | Description
    education_lines = [l.strip() for l in form.cleaned_data.get('education_raw', '').splitlines() if l.strip()]
    for line in education_lines:
        parts = [p.strip() for p in line.split('|')]
        Education.objects.create(
            resume=resume,
            degree=parts[0] if len(parts) > 0 else '',
            institution=parts[1] if len(parts) > 1 else '',
            year=parts[2] if len(parts) > 2 else '',
            description=parts[3] if len(parts) > 3 else '',
        )

    # Experience: Role | Company | Duration | Location | Description
    experience_lines = [l.strip() for l in form.cleaned_data.get('experience_raw', '').splitlines() if l.strip()]
    for line in experience_lines:
        parts = [p.strip() for p in line.split('|')]
        Experience.objects.create(
            resume=resume,
            role=parts[0] if len(parts) > 0 else '',
            company=parts[1] if len(parts) > 1 else '',
            duration=parts[2] if len(parts) > 2 else '',
            location=parts[3] if len(parts) > 3 else '',
            description=parts[4] if len(parts) > 4 else '',
        )

    # Projects: Title | Technologies | Description
    project_lines = [l.strip() for l in form.cleaned_data.get('projects_raw', '').splitlines() if l.strip()]
    for line in project_lines:
        parts = [p.strip() for p in line.split('|')]
        Project.objects.create(
            resume=resume,
            name=parts[0] if len(parts) > 0 else '',
            technologies=parts[1] if len(parts) > 1 else '',
            description=parts[2] if len(parts) > 2 else '',
        )

    # Certifications: Title | Issuer | Year
    certification_lines = [l.strip() for l in form.cleaned_data.get('certifications_raw', '').splitlines() if l.strip()]
    for line in certification_lines:
        parts = [p.strip() for p in line.split('|')]
        Certification.objects.create(
            resume=resume,
            name=parts[0] if len(parts) > 0 else '',
            authority=parts[1] if len(parts) > 1 else '',
            year=parts[2] if len(parts) > 2 else '',
        )

    # Achievements: one per line
    achievement_lines = [l.strip() for l in form.cleaned_data.get('achievements_raw', '').splitlines() if l.strip()]
    for line in achievement_lines:
        Achievement.objects.create(resume=resume, title=line)


@login_required
def resume_create(request):
    if request.method == 'POST':
        form = ResumeForm(request.POST, request.FILES)
        if form.is_valid():
            resume = form.save(commit=False)
            resume.user = request.user
            resume.save()

            # Optionally enhance summary with AI
            ai = AIEngine()
            if resume.summary and len(resume.summary.strip()) > 20 and "I don't see" not in resume.summary:
                ai.improve_summary(resume)
            else:
                summaries = ai.generate_summaries(resume)
                resume.summary = summaries.get('professional', '')
                resume.save()

            return redirect('resumes:resume_detail', pk=resume.pk)
    else:
        form = ResumeForm()
    return render(request, 'resumes/resume_create.html', {'form': form})


@login_required
def manual_builder(request):
    if request.method == 'POST':
        form = ManualResumeForm(request.POST)
        if form.is_valid():
            resume = form.save(commit=False)
            resume.user = request.user
            resume.save()
            parse_manual_fields(resume, form)

            # Optionally enhance with AI
            ai = AIEngine()
            if not resume.summary or len(resume.summary.strip()) < 20 or "I don't see" in resume.summary:
                summaries = ai.generate_summaries(resume)
                resume.summary = summaries.get('professional', '')
                resume.save()
            return redirect('resumes:resume_detail', pk=resume.pk)
    else:
        form = ManualResumeForm()
    return render(request, 'resumes/manual_resume_builder.html', {'form': form})


@login_required
def resume_detail(request, pk):
    resume = get_object_or_404(Resume, pk=pk, user=request.user)
    jd_form = JobDescriptionForm()
    analysis = resume.ats_analyses.order_by('-created_at').first()
    generated = resume.generated_resumes.order_by('-created_at').first()

    if request.method == 'POST':
        jd_form = JobDescriptionForm(request.POST, request.FILES)
        if jd_form.is_valid():
            uploaded_file = request.FILES.get('resume_file')
            description_text = jd_form.cleaned_data['description']
            
            # Save file & extract text
            resume.resume_file = uploaded_file
            resume.save()
            resume_text = extract_text_from_file(uploaded_file)
            
            # Call AI parser
            ai = AIEngine()
            parsed_data = ai.parse_resume_text(resume_text)
            if parsed_data:
                # Update basic fields
                resume.full_name = parsed_data.get('full_name', resume.full_name or '')
                resume.title = parsed_data.get('title', resume.title or '')
                resume.summary = parsed_data.get('summary', resume.summary or '')
                resume.contact_email = parsed_data.get('contact_email', resume.contact_email or '')
                resume.contact_phone = parsed_data.get('contact_phone', resume.contact_phone or '')
                resume.save()
                
                # Update skills
                skills = parsed_data.get('skills', [])
                if skills:
                    resume.skills.all().delete()
                    for skill_name in skills:
                        Skill.objects.create(resume=resume, name=skill_name)
                
                # Update experiences
                experiences = parsed_data.get('experiences', [])
                if experiences:
                    resume.experiences.all().delete()
                    for exp in experiences:
                        Experience.objects.create(
                            resume=resume,
                            role=exp.get('role', ''),
                            company=exp.get('company', ''),
                            duration=exp.get('duration', ''),
                            location=exp.get('location', ''),
                            description=exp.get('description', ''),
                        )
                
                # Update projects
                projects = parsed_data.get('projects', [])
                if projects:
                    resume.projects.all().delete()
                    for proj in projects:
                        Project.objects.create(
                            resume=resume,
                            name=proj.get('name', ''),
                            technologies=proj.get('technologies', ''),
                            description=proj.get('description', ''),
                        )
            else:
                # Fallback if AI parsing fails
                if resume_text:
                    resume.summary = resume_text[:1000]
                    resume.save()
            
            # Create JobDescription
            job_desc = JobDescription.objects.create(
                user=request.user,
                title=resume.title or "Target Role",
                description=description_text
            )
            
            # Run scoring and redirect
            analysis = score_resume(resume, job_desc)
            return redirect('resumes:resume_detail', pk=resume.pk)

    return render(request, 'resumes/resume_detail.html', {
        'resume': resume,
        'jd_form': jd_form,
        'analysis': analysis,
        'generated': generated,
    })


def _get_generated_resume_html(resume, template_style='corporate'):
    """Get the HTML for a generated resume."""
    generated = resume.generated_resumes.filter(template_style=template_style).order_by('-created_at').first()
    if generated:
        return generated.html_content or generated.content_html or None
    return None


@login_required
def resume_preview(request, pk, template_style='corporate'):
    resume = get_object_or_404(Resume, pk=pk, user=request.user)
    html = _get_generated_resume_html(resume, template_style)
    if not html:
        html = build_template_html(resume, template_style)
    return render(request, 'resumes/resume_preview.html', {
        'resume': resume,
        'html_content': html,
        'template_style': template_style,
    })


@login_required
def download_resume_pdf(request, pk, template_style='corporate'):
    resume = get_object_or_404(Resume, pk=pk, user=request.user)
    html = _get_generated_resume_html(resume, template_style)
    if not html:
        html = build_template_html(resume, template_style)
    try:
        from weasyprint import HTML
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as output:
            HTML(string=html).write_pdf(output.name)
        with open(output.name, 'rb') as f:
            pdf_data = f.read()
        os.unlink(output.name)
    except Exception:
        try:
            pdf_data = _generate_pdf_bytes_with_reportlab(resume)
        except Exception as e:
            raise Http404(f'PDF generation failed: {e}')
    response = HttpResponse(pdf_data, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{resume.title}_{template_style}.pdf"'
    return response


def _generate_pdf_bytes_with_reportlab(resume):
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.utils import simpleSplit
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    width, height = letter
    c = canvas.Canvas(buffer, pagesize=letter)
    x, y = 72, height - 72

    c.setFont('Helvetica-Bold', 18)
    c.drawString(x, y, resume.full_name or resume.title)
    y -= 28

    c.setFont('Helvetica', 11)
    if resume.summary:
        for line in simpleSplit(resume.summary, 'Helvetica', 10, width - 2 * x):
            c.drawString(x, y, line)
            y -= 14
        y -= 10

    c.save()
    buffer.seek(0)
    return buffer.read()


@login_required
def resume_chat(request, pk):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    resume = get_object_or_404(Resume, pk=pk, user=request.user)
    try:
        data = json.loads(request.body)
        message = data.get('message')
        if not message:
            return JsonResponse({'error': 'No message provided'}, status=400)

        ai = AIEngine()
        user_display_name = request.user.first_name or request.user.username
        
        # Extract latest job description and missing skills
        analysis = resume.ats_analyses.order_by('-created_at').first()
        job_desc_text = analysis.job_description.description if (analysis and analysis.job_description) else ""
        missing_skills = analysis.missing_keywords if analysis else []
        
        result = ai.chat_edit_resume(
            resume, 
            message, 
            user_name=user_display_name, 
            job_desc=job_desc_text, 
            missing_skills=missing_skills
        )

        explanation = result.get('explanation', 'Resume updated.')
        updates = result.get('updates', {})
        skill_updates = result.get('skill_updates', [])
        exp_updates = result.get('experience_updates', [])

        # Apply basic field updates
        for field, value in updates.items():
            if hasattr(resume, field):
                setattr(resume, field, value)
        resume.save()

        # Apply skill updates
        if skill_updates:
            resume.skills.all().delete()
            for skill_name in skill_updates:
                Skill.objects.create(resume=resume, name=skill_name)

        # Apply experience updates
        if exp_updates:
            resume.experiences.all().delete()
            for exp in exp_updates:
                Experience.objects.create(
                    resume=resume,
                    role=exp.get('role', ''),
                    company=exp.get('company', ''),
                    description=exp.get('description', exp.get('bullets', '')),
                )

        return JsonResponse({'explanation': explanation, 'status': 'success'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
