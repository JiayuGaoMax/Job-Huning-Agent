from asyncio import log
from pathlib import Path
from xml.sax.saxutils import escape
import json
from ollama import chat
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from JobData import UNWANTED_WEB_WORDS
import re
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from PlaywrightLib import get_html_playwright,html_to_text
from dist.JobHuntingAgent._internal import fitz


OUTPUT_DIR = Path(__file__).resolve().parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def safe_text(value) -> str:
    """Escape text so symbols do not break ReportLab paragraphs."""
    return escape(str(value or ""))


def add_bullet_list(story, bullets, bullet_style):
    """Add a compact bullet list to the PDF."""
    clean_bullets = [
        bullet.strip()
        for bullet in bullets
        if bullet and bullet.strip()
    ]

    if not clean_bullets:
        return

    story.append(
        ListFlowable(
            [
                ListItem(
                    Paragraph(safe_text(bullet), bullet_style),
                    leftIndent=8,
                )
                for bullet in clean_bullets
            ],
            bulletType="bullet",
            start="circle",
            leftIndent=14,
            bulletFontName="Helvetica",
            bulletFontSize=6,
            bulletOffsetY=1,
            spaceBefore=1,
            spaceAfter=4,
        )
    )


def add_section_heading(story, title, section_style):
    """Add a section title with a divider line."""
    story.append(Spacer(1, 4))
    story.append(Paragraph(title.upper(), section_style))
    story.append(
        HRFlowable(
            width="100%",
            thickness=0.8,
            color=colors.HexColor("#2F5D7C"),
            spaceBefore=1,
            spaceAfter=4,
        )
    )


def generate_resume_pdf(resume_data: dict, output_filename: str) -> Path:
    output_path = OUTPUT_DIR / output_filename

    document = SimpleDocTemplate(
        str(output_path),
        pagesize=LETTER,
        leftMargin=0.55 * inch,
        rightMargin=0.55 * inch,
        topMargin=0.42 * inch,
        bottomMargin=0.42 * inch,
        title=f"{resume_data.get('name', 'Candidate')} Resume",
        author=resume_data.get("name", "Candidate"),
    )

    styles = getSampleStyleSheet()

    name_style = ParagraphStyle(
        "NameStyle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=22,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#183B56"),
        spaceAfter=2,
    )

    headline_style = ParagraphStyle(
        "HeadlineStyle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=12,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#3D5A6C"),
        spaceAfter=3,
    )

    contact_style = ParagraphStyle(
        "ContactStyle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.7,
        leading=10,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#444444"),
        spaceAfter=7,
    )

    section_style = ParagraphStyle(
        "SectionStyle",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=10.5,
        leading=12,
        alignment=TA_LEFT,
        textColor=colors.HexColor("#183B56"),
        spaceBefore=0,
        spaceAfter=0,
    )

    body_style = ParagraphStyle(
        "BodyStyle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=11.2,
        textColor=colors.HexColor("#222222"),
        spaceAfter=3,
    )

    bullet_style = ParagraphStyle(
        "BulletStyle",
        parent=body_style,
        fontSize=8.8,
        leading=10.8,
        leftIndent=0,
        firstLineIndent=0,
        spaceAfter=1.5,
    )

    role_style = ParagraphStyle(
        "RoleStyle",
        parent=body_style,
        fontName="Helvetica-Bold",
        fontSize=9.4,
        leading=11,
        textColor=colors.HexColor("#183B56"),
        spaceAfter=0,
    )

    company_style = ParagraphStyle(
        "CompanyStyle",
        parent=body_style,
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=11,
        textColor=colors.HexColor("#333333"),
        spaceAfter=0,
    )

    date_style = ParagraphStyle(
        "DateStyle",
        parent=body_style,
        fontName="Helvetica",
        fontSize=8.6,
        leading=10,
        alignment=TA_LEFT,
        textColor=colors.HexColor("#555555"),
        spaceAfter=0,
    )

    skill_label_style = ParagraphStyle(
        "SkillLabelStyle",
        parent=body_style,
        fontName="Helvetica-Bold",
        fontSize=8.8,
        leading=10.5,
        textColor=colors.HexColor("#183B56"),
        spaceAfter=0,
    )

    skill_value_style = ParagraphStyle(
        "SkillValueStyle",
        parent=body_style,
        fontSize=8.8,
        leading=10.5,
        spaceAfter=0,
    )

    story = []

    story.append(
        Paragraph(
            safe_text(resume_data.get("name", "Jordan Taylor")),
            name_style,
        )
    )

    headline = resume_data.get("headline", "")
    if headline:
        story.append(Paragraph(safe_text(headline), headline_style))


    contact = resume_data.get("contact", {})

    contact_parts = []

    location = contact.get("location")
    phone = contact.get("phone")
    email = contact.get("email")
    linkedin = contact.get("linkedin")
    github = contact.get("github")

    if location:
        contact_parts.append(safe_text(location))

    if phone:
        contact_parts.append(safe_text(phone))

    if email:
        safe_email = safe_text(email)
        contact_parts.append(
            f'<link href="mailto:{safe_email}"><u>{safe_email}</u></link>'
        )

    if linkedin and linkedin != "Ready to insert":
        safe_linkedin = safe_text(linkedin)
        contact_parts.append(
            f'<link href="{safe_linkedin}"><u>LinkedIn</u></link>'
        )

    if github and github != "Ready to insert":
        safe_github = safe_text(github)
        contact_parts.append(
            f'<link href="{safe_github}"><u>GitHub</u></link>'
        )

    contact_line = " | ".join(contact_parts)

    if contact_line:
        story.append(Paragraph(contact_line, contact_style))

    summary = resume_data.get("professional_summary", "")

    if isinstance(summary, dict):
        summary = summary.get("professional_summary", "")

    if summary:
        add_section_heading(story, "Professional Summary", section_style)
        story.append(Paragraph(safe_text(summary), body_style))

    skill_groups = resume_data.get("skill_groups", {})
    if skill_groups:
        add_section_heading(story, "Technical Skills", section_style)

        skill_rows = []

        for category, values in skill_groups.items():
            if isinstance(values, list):
                value_text = ", ".join(values)
            else:
                value_text = str(values)

            skill_rows.append(
                [
                    Paragraph(safe_text(category), skill_label_style),
                    Paragraph(safe_text(value_text), skill_value_style),
                ]
            )

        skills_table = Table(
            skill_rows,
            colWidths=[1.15 * inch, 5.95 * inch],
            hAlign="LEFT",
        )

        skills_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 1),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ]
            )
        )

        story.append(skills_table)
# Work Experience Section
    experience = resume_data.get("experience", [])

    if experience:
        add_section_heading(story, "Professional Experience", section_style)

        for role in experience:
            role_heading = Table(
                [
                    [
                        Paragraph(
                            safe_text(role.get("title", "")),
                            role_style,
                        ),
                        Paragraph(
                            safe_text(role.get("dates", "")),
                            date_style,
                        ),
                    ]
                ],
                colWidths=[5.4 * inch, 1.7 * inch],
            )

            role_heading.setStyle(
                TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                        ("TOPPADDING", (0, 0), (-1, -1), 0),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ]
                )
            )

            company_location = " | ".join(
                value
                for value in [
                    role.get("company"),
                    role.get("location"),
                ]
                if value
            )

            role_block = [
                role_heading,
                Paragraph(
                    safe_text(company_location),
                    company_style,
                ),
            ]

            bullets = role.get("bullets", [])

            if bullets:
                temp_story = []
                add_bullet_list(temp_story, bullets, bullet_style)
                role_block.extend(temp_story)

            story.append(KeepTogether(role_block))


    #Education Section
    education = resume_data.get("education", [])
    if education:
        add_section_heading(story, "Education", section_style)

        for item in education:
            degree_school = " - ".join(
                value
                for value in [
                    item.get("degree"),
                    item.get("school"),
                ]
                if value
            )

            education_heading = Table(
                [
                    [
                        Paragraph(
                            safe_text(degree_school),
                            role_style,
                        ),
                        Paragraph(
                            safe_text(item.get("dates", "")),
                            date_style,
                        ),
                    ]
                ],
                colWidths=[5.4 * inch, 1.7 * inch],
            )

            education_heading.setStyle(
                TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                        ("TOPPADDING", (0, 0), (-1, -1), 0),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ]
                )
            )

            story.append(education_heading)

            details = item.get("details", "")
            if details:
                story.append(Paragraph(safe_text(details), body_style))

    projects = resume_data.get("projects", [])
    if projects:
        add_section_heading(story, "Selected Projects", section_style)

        for project in projects:
            project_heading = project.get("name", "")

            if project.get("technologies"):
                project_heading += (
                    " | " + ", ".join(project["technologies"])
                )

            story.append(
                Paragraph(
                    safe_text(project_heading),
                    role_style,
                )
            )

            add_bullet_list(
                story,
                project.get("bullets", []),
                bullet_style,
            )
    if resume_data.get("leadership_and_volunteering"):
        add_section_heading(
            story, "Leadership and Volunteering", section_style
        )

        for item in resume_data["leadership_and_volunteering"]:
            role_org = " - ".join(
                value
                for value in [
                    item.get("role"),
                    item.get("organization"),
                ]
                if value
            )

            leadership_heading = Table(
                [
                    [
                        Paragraph(
                            safe_text(role_org),
                            role_style,
                        ),
                        Paragraph(
                            safe_text(item.get("dates", "")),
                            date_style,
                        ),
                    ]
                ],
                colWidths=[5.4 * inch, 1.7 * inch],
            )

            leadership_heading.setStyle(
                TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                        ("TOPPADDING", (0, 0), (-1, -1), 0),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ]
                )
            )

            story.append(leadership_heading)

            add_bullet_list(
                story,
                item.get("bullets", []),
                bullet_style,
            )
    '''
    certifications = resume_data.get("certifications", [])
    if certifications:
        add_section_heading(story, "Certifications", section_style)
        story.append(
            Paragraph(
                safe_text(" | ".join(certifications)),
                body_style,
            )
        )
        '''

    document.build(story)

    return output_path

def generate_skills_section(
    master_resume_text: str,
    job_posting_text: str,
    model: str = "qwen3:8b",
) -> dict:
    prompt = f"""
You are a strict resume customization assistant.

Generate ONLY the TECHNICAL SKILLS section.

Rules:
- Use only skills clearly supported by the master resume.
- Do not invent technologies or tools.
- Order skills by relevance to the target job.
- Remove empty or irrelevant categories.
- Return valid JSON only.
- Do not include Markdown or explanations.

Return this structure:

{{
  "Programming": [],
  "Databases": [],
  "Reporting and Analytics": [],
  "Development Tools": [],
  "Web and Infrastructure": [],
  "AI and Automation": []
}}

MASTER RESUME:
{master_resume_text}

TARGET JOB POSTING:
{job_posting_text}
"""

    response = chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        format="json",
        options={
            "temperature": 0,
            "num_ctx": 16384,
        },
    )

    return json.loads(response.message.content)

def generate_experience_section(
    master_resume_text: str,
    job_posting_text: str,
    model: str = "qwen3:8b",
) -> dict:
    prompt = f"""
You are a strict resume customization assistant.

Generate ONLY the PROFESSIONAL EXPERIENCE section.

Rules:
- Use only experience clearly supported by the master resume.
- Do not invent employers, job titles, dates, locations, technologies,
  responsibilities, achievements, or metrics.
- Preserve the original employer names, job titles, dates, and locations.
- Rewrite bullets to emphasize experience relevant to the target job.
- Use concise, professional, accomplishment-focused language.
- Begin each bullet with a strong action verb.
- Include measurable results only when they are explicitly supported
  by the master resume.
- Do not repeat the same achievement across multiple bullets.
- Remove weak, irrelevant, or unsupported bullets.
- Keep each role to a maximum of 6 bullets.
- Return roles in reverse chronological order.
- Return valid JSON only.
- Do not include Markdown or explanations.

Return this structure:

{{
  "experience": [
    {{
      "title": "",
      "company": "",
      "location": "",
      "dates": "",
      "bullets": []
    }}
  ]
}}

MASTER RESUME:
{master_resume_text}

TARGET JOB POSTING:
{job_posting_text}
"""

    response = chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        format="json",
        options={
            "temperature": 0,
            "num_ctx": 16384,
        },
    )

    result = json.loads(response.message.content)

    if not isinstance(result, dict):
        raise ValueError("Model response must be a JSON object.")

    experience = result.get("experience")

    if not isinstance(experience, list):
        raise ValueError(
            "Model response must contain an 'experience' list."
        )

    for role in experience:
        if not isinstance(role, dict):
            raise ValueError("Each experience entry must be a JSON object.")

        required_fields = {
            "title",
            "company",
            "location",
            "dates",
            "bullets",
        }

        missing_fields = required_fields - role.keys()

        if missing_fields:
            raise ValueError(
                f"Experience entry is missing fields: "
                f"{sorted(missing_fields)}"
            )

        if not isinstance(role["bullets"], list):
            raise ValueError(
                "Each experience entry must contain a bullets list."
            )

    return result

def sample_resume_data() -> dict:
    """
    Base resume data using known information.

    Fields marked "Ready to insert" should be replaced manually
    or populated later by your resume customizer.
    """

    return {
        "name": "Max (Jiayu) Gao",

        "headline": (
            "Software Developer | AI Automation | Data and Business Systems"
        ),

        "contact": {
            "location": "Regina, Saskatchewan, Canada",
            "phone": "306-501-1257",
            "email": "JiayuGaoMax@gmail.com",
            "linkedin": "https://www.linkedin.com/in/jiayugaomax/",
            "github": "https://github.com/JiayuGaoMax",
        },

        "professional_summary": (
            "Software developer with experience supporting and improving "
            "enterprise business systems, database processes, reporting "
            "solutions, and workflow automation. Experienced with Python, "
            ".NET, VB.NET, Oracle, SQL, Power BI, SSRS, and AI-assisted "
            "development. Demonstrated ability to improve data-processing "
            "performance, build practical prototypes, troubleshoot technical "
            "issues, and translate business needs into working software. "
            "Currently developing local-AI tools for job extraction, document "
            "analysis, resume matching, and automated resume customization."
        ),

        "skill_groups": {
            "Programming": [
                "Python",
                "C++",
                "Java",
                "JavaScript",
                "PHP",
                "VB.NET",
                "PowerShell",
            ],

            "Databases": [
                "Oracle",
                "MySQL",
                "MongoDB",
                "SQL",
                "Database Maintenance",
                "Data Loading",
            ],

            "Reporting and Analytics": [
                "Power BI",
                "SSRS",
                "Data Analysis",
                "Dashboard Development",
                "Business Reporting",
            ],

            "Development Tools": [
                "Visual Studio",
                "Git",
                "Eclipse",
                "Android Studio",
                "Linux",
                "Windows",
            ],

            "Web and Infrastructure": [
                "Apache",
                "Nginx",
                "Home Web Server",
                "VPN",
                "HTML Parsing",
                "Playwright",
                "BeautifulSoup",
            ],

            "AI and Automation": [
                "Ollama",
                "Local Language Models",
                "Prompt Engineering",
                "Document Extraction",
                "Resume Matching",
                "AI Workflow Automation",
                "Embeddings",
                "Retrieval-Augmented Generation",
            ],
        },

        "experience": [
            {
                "title": "Software Developer",
                "company": "Canada Life Reinsurance",
                "location": "Regina, Saskatchewan",
                "dates": "Ready to insert",
                "bullets": [
                    (
                        "Improved a bulk data-loading process by approximately "
                        "10x through multithreading and performance optimization."
                    ),
                    (
                        "Supported and enhanced enterprise business applications "
                        "using .NET, VB.NET, SQL, and Oracle technologies."
                    ),
                    (
                        "Performed database-related development, maintenance, "
                        "troubleshooting, and data-processing work."
                    ),
                    (
                        "Investigated application and data issues and developed "
                        "practical fixes for business users."
                    ),
                    (
                        "Worked with internal stakeholders to understand business "
                        "requirements and improve system workflows."
                    ),
                    (
                        "Additional role-specific achievement ready to insert."
                    ),
                ],
            },

            {
                "title": "Information Technology Co-op Student",
                "company": "Co-op Refinery Complex",
                "location": "Regina, Saskatchewan",
                "dates": "2019",
                "bullets": [
                    (
                        "Created an OutSystems prototype for an employee leave "
                        "management process."
                    ),
                    (
                        "Built a Power BI and SSRS forecasting solution within "
                        "approximately three days."
                    ),
                    (
                        "Developed an Android barcode-scanning application for "
                        "RealWear wearable devices."
                    ),
                    (
                        "Created and supported PowerShell automation jobs."
                    ),
                    (
                        "Additional project or achievement ready to insert."
                    ),
                ],
            },

            {
                "title": "Information Technology Co-op Student",
                "company": "Saskatchewan Government Insurance",
                "location": "Regina, Saskatchewan",
                "dates": "2018",
                "bullets": [
                    (
                        "Supported more than 300 employee workstations and related "
                        "desktop technology."
                    ),
                    (
                        "Completed more than 40 network-related service orders."
                    ),
                    (
                        "Resolved more than 70 hardware support tickets."
                    ),
                    (
                        "Installed, configured, and supported computer peripherals "
                        "and workplace technology."
                    ),
                    (
                        "Additional support achievement ready to insert."
                    ),
                ],
            },

            {
                "title": "Senior Technology Tutor",
                "company": "Regina Public Library",
                "location": "Regina, Saskatchewan",
                "dates": "Ready to insert",
                "bullets": [
                    (
                        "Provided one-on-one technology support and instruction "
                        "to seniors and community members."
                    ),
                    (
                        "Helped users with computers, mobile devices, internet "
                        "services, online safety, and common technical problems."
                    ),
                    (
                        "Received positive feedback, including five-star ratings "
                        "for technology support sessions."
                    ),
                    (
                        "Additional volunteer achievement ready to insert."
                    ),
                ],
            },
        ],

        "education": [
            {
                "degree": "Bachelor of Science in Computer Science, Co-operative Education",
                "school": "University of Regina",
                "dates": "2014 - 2019",
                "details": (
                    "Computer Science major GPA: 4.0. Overall GPA: 3.7. "
                    "Relevant studies included software development, databases, "
                    "algorithms, networking, computer graphics, and systems."
                ),
            }
        ],

        "projects": [
            {
                "name": "AI Job-Hunting Agent",
                "technologies": [
                    "Python",
                    "Ollama",
                    "Playwright",
                    "BeautifulSoup",
                    "Local LLMs",
                    "ReportLab",
                ],
                "bullets": [
                    (
                        "Developed a Python-based agent that visits employer "
                        "career websites, extracts page content, identifies job "
                        "postings, and produces structured job records."
                    ),
                    (
                        "Added retry logic, company-level separation, structured "
                        "parsing, and model-based verification."
                    ),
                    (
                        "Started developing automated resume matching and "
                        "job-specific PDF resume generation."
                    ),
                    (
                        "Project result or repository URL ready to insert."
                    ),
                ],
            },

            {
                "name": "Local Large Language Model Project",
                "technologies": [
                    "Ollama",
                    "Local LLM",
                    "Python",
                    "Prompt Engineering",
                ],
                "bullets": [
                    (
                        "Built and tested a local language-model workflow using "
                        "approximately 7-billion-parameter models."
                    ),
                    (
                        "Experimented with document extraction, verification, "
                        "structured output, and local AI automation."
                    ),
                    (
                        "Performance measurement ready to insert."
                    ),
                ],
            },

            {
                "name": "Document Search and Retrieval Prototype",
                "technologies": [
                    "Python",
                    "Embeddings",
                    "Vector Search",
                    "RAG",
                ],
                "bullets": [
                    (
                        "Designed a document-search workflow that converts user "
                        "questions and document chunks into embeddings."
                    ),
                    (
                        "Used similarity matching to retrieve relevant document "
                        "sections before generating an answer with an LLM."
                    ),
                    (
                        "Dataset size or accuracy result ready to insert."
                    ),
                ],
            },

            {
                "name": "SIR Disease Simulation Model",
                "technologies": [
                    "Python",
                    "Mathematical Modelling",
                    "Data Visualization",
                ],
                "bullets": [
                    (
                        "Created a Python implementation of a susceptible, "
                        "infected, and recovered disease-spread model."
                    ),
                    (
                        "Additional technical details ready to insert."
                    ),
                ],
            },

            {
                "name": "C++ Ray Tracer",
                "technologies": [
                    "C++",
                    "Computer Graphics",
                    "Object-Oriented Programming",
                ],
                "bullets": [
                    (
                        "Developed a C++ ray-tracing project for rendering "
                        "three-dimensional scenes."
                    ),
                    (
                        "Rendering features and performance details ready to insert."
                    ),
                ],
            },

            {
                "name": "Home Web Server and VPN",
                "technologies": [
                    "Linux",
                    "Apache",
                    "Nginx",
                    "Networking",
                    "VPN",
                ],
                "bullets": [
                    (
                        "Configured and maintained a home-hosted web server and "
                        "private networking environment."
                    ),
                    (
                        "Security configuration details ready to insert."
                    ),
                ],
            },

            {
                "name": "3D Printer Assembly",
                "technologies": [
                    "Hardware Assembly",
                    "Troubleshooting",
                    "Calibration",
                ],
                "bullets": [
                    (
                        "Assembled, configured, and calibrated a functional "
                        "3D printer."
                    ),
                    (
                        "Printer model and completed builds ready to insert."
                    ),
                ],
            },
        ],

        "leadership_and_volunteering": [
            {
                "role": "Communications Director",
                "organization": "Regina Ski Club",
                "dates": "2026",
                "bullets": [
                    (
                        "Prepared communications and promotional materials for "
                        "club activities, ski trips, youth programs, and social events."
                    ),
                    (
                        "Helped communicate events involving more than 160 unique "
                        "participants."
                    ),
                ],
            },

            {
                "role": "Social Director",
                "organization": "Regina Ski Club",
                "dates": "2025",
                "bullets": [
                    (
                        "Helped organize member events, community activities, "
                        "refreshments, and volunteer initiatives."
                    )
                ],
            },

            {
                "role": "Vice President Public Relations",
                "organization": "Wascana Toastmasters",
                "dates": "2023",
                "bullets": [
                    (
                        "Supported public communications, event promotion, and "
                        "club visibility."
                    )
                ],
            },
            {
                "role": "Senior Technology Tutor",
                "organization": "Regina Public Library",
                "dates": "2023 - 2025",
                "bullets": [
                    (
                        "Provided one-on-one technology support and instruction "
                        "to seniors and community members."
                    ),
                    (
                        "Helped users with computers, mobile devices, internet "
                        "services, online safety, and common technical problems."
                    ),
                    (
                        "Received positive feedback, including five-star ratings "
                        "for technology support sessions."
                    ),
                ],
            },
        ],

        "certifications": [
            "Ready to insert",
        ],

        "awards": [
            "Ready to insert",
        ],

        "languages": [
            "English",
            "Mandarin Chinese",
            "Basic Vietnamese",
        ],

        "target_job": {
            "company": "Ready to insert",
            "job_title": "Ready to insert",
            "job_url": "Ready to insert",
            "job_keywords": [
                "Ready to insert",
            ],
        },

        "customization_notes": {
            "target_summary": "Ready to insert",
            "priority_skills": [
                "Ready to insert",
            ],
            "selected_experience_bullets": [
                "Ready to insert",
            ],
            "selected_projects": [
                "Ready to insert",
            ],
            "keywords_to_include": [
                "Ready to insert",
            ],
            "unsupported_requirements": [
                "Ready to insert",
            ],
        },
    }



def summarize_resume_for_job(
    master_resume_text: str,
    job_posting_text: str,
    model: str = "llama3.1:8b",
) -> str:
    fallback = """
TARGET POSITIONING
- Software Developer with enterprise application, database, reporting, automation, and production support experience.

RELEVANT SUMMARY POINTS
- 5+ years of experience supporting enterprise applications and business systems.
- Experience with SQL, Oracle, Python, .NET, VB.NET, Power BI, SSRS, troubleshooting, documentation, and production support.
- Experience translating business requirements into practical technical solutions.

RELEVANT SKILLS
- SQL
- Oracle
- Python
- .NET
- VB.NET
- Power BI
- SSRS
- Requirements Analysis
- Technical Documentation
- Production Support
- Troubleshooting
- Automation

RELEVANT EXPERIENCE TO EMPHASIZE
- Canada Life Reinsurance: enterprise application development, SQL/Oracle, production support, troubleshooting, documentation, performance optimization.
- Co-op Refinery Complex: Power BI, SSRS, automation, reporting, prototype development.
- SGI: enterprise IT support, troubleshooting, user support.
- SLGA: junior programmer analyst experience, SQL, Oracle, application support.

RELEVANT PROJECTS
- AI Job Discovery Platform: Python automation, job extraction, structured data processing.
- AI Resume Customizer: Python, prompt engineering, structured resume generation.
- Document Search and Retrieval Prototype: embeddings, vector similarity, RAG concepts.

SKILLS TO REMOVE OR DEPRIORITIZE
- Skills unrelated to the target job should be removed or moved lower.

UNSUPPORTED REQUIREMENTS
- Any job requirements not clearly supported by the master resume should not be added.
""".strip()

    for attempt in range(3):
        prompt = f"""
You are a strict resume filtering assistant.

Create a shorter, job-focused version of the candidate's master resume.

Use point form only.

Rules:
- Use only information clearly supported by the master resume.
- Do not invent skills, tools, job titles, employers, dates, certifications, or achievements.
- Remove skills that are unnecessary for the target job.
- Keep transferable skills if they are useful for the job.
- Do not add required job skills unless they appear in the master resume.
- If the job asks for a missing skill, list it under UNSUPPORTED REQUIREMENTS.
- Keep the candidate's real background realistic.
- Do not overstate seniority or specialization.
- Do not use JSON.
- Do not use markdown tables.
- Use clear section headings and bullet points.

Use this structure:

TARGET POSITIONING
- ...

RELEVANT SUMMARY POINTS
- ...

RELEVANT SKILLS
- ...

RELEVANT EXPERIENCE TO EMPHASIZE
- ...

RELEVANT PROJECTS
- ...

LEADERSHIP OR VOLUNTEER RELEVANCE
- ...

SKILLS TO REMOVE OR DEPRIORITIZE
- ...

UNSUPPORTED REQUIREMENTS
- ...

MASTER RESUME:
{master_resume_text[:10000]}

TARGET JOB POSTING:
{job_posting_text[:6000]}
"""

        response = chat(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            options={
                "temperature": 0,
                "top_p": 0.1,
                "seed": 42 + attempt,
                "num_predict": 1200,
                "num_ctx": 12000,
            },
        )

        raw_response = response["message"]["content"].strip()

        if not raw_response:
            print(f"Resume summary attempt {attempt + 1}: empty response")
            continue

        if len(raw_response) < 200:
            print(f"Resume summary attempt {attempt + 1}: response too short")
            print(raw_response)
            continue

        return raw_response

    print("WARNING: Resume summary agent failed. Using fallback.")
    return fallback

def generate_headline_section(
    master_resume_text: str,
    job_posting_text: str,
    model: str = "llama3.1:8b",
) -> str:
    prompt = f"""
You are a resume headline writer.

Write one short resume headline for the candidate.

Rules:
- Return only the headline text.
- Do not return JSON.
- Do not use Markdown.
- Do not explain.
- Maximum 12 words.
- Use only facts supported by the master resume.
- Use the job posting only to decide relevance.
- Do not invent job titles, certifications, skills, or experience.

MASTER RESUME:
{master_resume_text}

JOB POSTING:
{job_posting_text}
"""

    response = chat(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "Return one short resume headline only.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        options={
            "temperature": 0.1,
            "num_ctx": 8192,
            "num_predict": 80,
        },
    )

    result = response.message.content.strip()

    if not result:
        return "Software Developer | Systems Integration | AI Automation"

    return result

def generate_experience_section(
    master_resume_text: str,
    job_posting_text: str,
    model: str = "qwen3:8b",
) -> dict:
    prompt = f"""
You are a strict resume customization assistant.

Generate ONLY the PROFESSIONAL EXPERIENCE section.

Rules:
- Use only experience clearly supported by the master resume.
- Do not invent employers, job titles, dates, locations, technologies,
  responsibilities, achievements, or metrics.
- Preserve the original employer names, job titles, dates, and locations.
- Rewrite bullets to emphasize experience relevant to the target job.
- Use concise, professional, accomplishment-focused language.
- Begin each bullet with a strong action verb.
- Include measurable results only when explicitly supported by the master resume.
- Do not repeat the same achievement across multiple bullets.
- Remove weak, irrelevant, or unsupported bullets.
- Keep each role to a maximum of 6 bullets.
- Return roles in reverse chronological order.
- Every item inside "bullets" must be one complete bullet-point string.
- Do not split one bullet into multiple list items.
- Do not include bullet symbols such as •, -, or *.
- Return valid JSON only.
- Do not include Markdown, Python syntax, parentheses, or explanations.

Return exactly this structure:

{{
  "experience": [
    {{
      "title": "",
      "company": "",
      "location": "",
      "dates": "",
      "bullets": [
        "First complete bullet point.",
        "Second complete bullet point."
      ]
    }}
  ]
}}

MASTER RESUME:
{master_resume_text}

TARGET JOB POSTING:
{job_posting_text}
"""

    response = chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        format="json",
        options={
            "temperature": 0,
            "num_ctx": 16384,
        },
    )

    result = json.loads(response.message.content)

    if not isinstance(result, dict):
        raise ValueError("Model response must be a JSON object.")

    experience = result.get("experience")

    if not isinstance(experience, list):
        raise ValueError(
            "Model response must contain an 'experience' list."
        )

    required_fields = {
        "title",
        "company",
        "location",
        "dates",
        "bullets",
    }

    for role in experience:
        if not isinstance(role, dict):
            raise ValueError(
                "Each experience entry must be a JSON object."
            )

        missing_fields = required_fields - role.keys()

        if missing_fields:
            raise ValueError(
                f"Experience entry is missing fields: "
                f"{sorted(missing_fields)}"
            )

        if not isinstance(role["bullets"], list):
            raise ValueError(
                "Each experience entry must contain a bullets list."
            )

        role["bullets"] = [
            bullet.strip()
            for bullet in role["bullets"]
            if isinstance(bullet, str) and bullet.strip()
        ]

    return result
def load_resume(pdf_path):
    doc = fitz.open(pdf_path)

    text = ""
    for page in doc:
        text += page.get_text()

    doc.close()
    return text



def generate_professional_summary(
    master_resume_text: str,
    job_posting_text: str,
    model: str = "llama3.1:8b",
) -> str:
    prompt = f"""
You are a professional resume writer.

Write a professional summary for the candidate's customized resume.

Rules:
- Return plain text only.
- Do not return JSON.
- Do not use Markdown.
- Do not explain.
- Write one paragraph.
- Use 3 sentences.
- Keep it under 90 words.
- Use only facts supported by the master resume.
- Use the job posting only to decide what to emphasize.
- Do not invent skills, job titles, certifications, metrics, or experience.

MASTER RESUME:
{master_resume_text}

JOB POSTING:
{job_posting_text}
"""

    response = chat(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "Return only one professional resume summary paragraph.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        options={
            "temperature": 0.1,
            "num_ctx": 8192,
            "num_predict": 300,
        },
    )

    result = response.message.content.strip()

    if not result:
        return (
            "Software developer with experience in enterprise systems, data processing, "
            "automation, and technical support. Skilled in translating business needs "
            "into practical technical solutions using programming, databases, reporting, "
            "and AI-assisted workflows."
        )

    return result

def clean_json_response(raw_text: str) -> str:
    raw_text = raw_text.strip()

    # Remove Markdown code fences if model returns ```json ... ```
    raw_text = re.sub(r"^```json\s*", "", raw_text, flags=re.IGNORECASE)
    raw_text = re.sub(r"^```\s*", "", raw_text)
    raw_text = re.sub(r"\s*```$", "", raw_text)

    # Extract only the JSON object if extra text exists
    start = raw_text.find("{")
    end = raw_text.rfind("}")

    if start != -1 and end != -1 and end > start:
        raw_text = raw_text[start:end + 1]

    return raw_text


def generate_projects_section(
    master_resume_text: str,
    job_posting_text: str,
    model: str = "llama3.1:8b",
) -> dict:
    prompt = f"""
You are a strict JSON-only resume section generator.

Generate ONLY the PROJECTS section for a customized resume.

SOURCE RULES:
- The MASTER RESUME is the only source of truth about the candidate.
- The TARGET JOB POSTING is only used to decide relevance and ordering.
- Do not copy job requirements into the candidate's experience.
- Do not invent technologies, metrics, URLs, project details, project names, dates, employers, or achievements.
- If a detail is not clearly supported by the master resume, omit it.

OUTPUT RULES:
- Return valid JSON only.
- Do not include Markdown.
- Do not include explanations.
- Do not include comments.
- Do not use trailing commas.
- Return exactly 2 projects.
- Do not start a third project.
- Each project must contain exactly these keys:
  - "name"
  - "technologies"
  - "bullets"
- "name" must be a string.
- "technologies" must be a list of strings.
- "bullets" must be a list of exactly 3 strings.
- Each bullet must be 15 to 30 words.
- Each bullet must start with a strong action verb.
- Do not use quotation marks inside bullet text.
- Do not include placeholder text like "ready to insert".
- After the second project, immediately close the projects array and close the JSON object.
- The response must end with these exact final characters:
  ]
}}

STYLE RULES:
- Order projects by relevance to the target job.
- Prefer projects related to Python, automation, AI, LLMs, JSON, APIs, Playwright, data extraction, PDF generation, or system design when supported.
- Keep wording professional and resume-ready.
- Avoid repeating the same idea across bullets.

Return exactly this JSON shape:

{{
  "projects": [
    {{
      "name": "Project Name",
      "technologies": [
        "Technology 1",
        "Technology 2"
      ],
      "bullets": [
        "Built a resume-ready project bullet using only facts supported by the master resume.",
        "Implemented another resume-ready project bullet using only facts supported by the master resume.",
        "Designed another resume-ready project bullet using only facts supported by the master resume."
      ]
    }},
    {{
      "name": "Project Name",
      "technologies": [
        "Technology 1",
        "Technology 2"
      ],
      "bullets": [
        "Built a resume-ready project bullet using only facts supported by the master resume.",
        "Implemented another resume-ready project bullet using only facts supported by the master resume.",
        "Designed another resume-ready project bullet using only facts supported by the master resume."
      ]
    }}
  ]
}}

MASTER RESUME:
<<<MASTER_RESUME_START
{master_resume_text}
MASTER_RESUME_END>>>

TARGET JOB POSTING:
<<<JOB_POSTING_START
{job_posting_text}
JOB_POSTING_END>>>
"""

    response = chat(
        model=model,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        format="json",
        options={
            "temperature": 0.0,
            "num_predict": 2048,
            "num_ctx": 16384,

        },
    )

    raw_response = response.message.content

    try:
        cleaned_response = clean_json_response(raw_response)
        data = json.loads(cleaned_response)

    except json.JSONDecodeError as exc:
        print("PROJECTS RAW LLM RESPONSE:")
        print(raw_response)

        with open(
            "bad_projects_response.txt",
            "w",
            encoding="utf-8",
        ) as file:
            file.write(raw_response)

        raise ValueError(
            "Project section returned invalid JSON. "
            "Raw response saved to bad_projects_response.txt"
        ) from exc

    if "projects" not in data:
        raise ValueError(
            "Missing 'projects' key:\n"
            + json.dumps(data, indent=2, ensure_ascii=False)
        )

    if not isinstance(data["projects"], list):
        raise ValueError("'projects' must be a list.")

    return data


def summarize_job_posting(
    webpage_text: str,
    model: str = "llama3.1:8b",
) -> str:
    prompt = f"""
You are a job-posting summarization assistant.

Analyze the webpage content and summarize only one specific job opportunity.

The webpage content may contain:
- Navigation menus
- Cookie notices
- Company information
- Repeated text
- Login buttons
- Application buttons
- Footer links
- Accessibility text
- Unrelated job listings

Ignore unrelated webpage content.

Write a short plain-text summary of the job posting.

Rules:
- Do not return JSON.
- Do not use Markdown.
- Do not use bullet points.
- Do not include explanations about your process.
- Do not invent missing information.
- Summarize into simple sentences.
- Keep it concise.
- Include job title, company, location, employment type, salary, main responsibilities, required skills, education, and experience when available.
- Do not copy long paragraphs from the job posting.
- Maximum 250 words.

WEBPAGE CONTENT:
{webpage_text}
"""

    response = chat(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You summarize job postings into short plain text. "
                    "Do not return JSON or Markdown."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        options={
            "temperature": 0.1,
            "num_ctx": 8192,
            "num_predict": 1024,
        },
    )

    return response.message.content.strip()


def generate_resume_from_url(
    job_url: str,
    master_resume_path: str = "Max_Gao_Master_Resume.pdf",
    output_filename: str = "sample_resume_template.pdf",
    model: str = "llama3.1:8b",
    log_callback=None,
) -> str:
    def log(message: str) -> None:
        if log_callback:
            log_callback(message)
        else:
            print(message)

    log("Step 1: Loading base resume data...")
    resume_data = sample_resume_data()



    log("Step 2: Reading job webpage...")
    webpage_html = get_html_playwright(job_url)

    log("Step 3: Cleaning webpage text...")
    webpage_text = html_to_text(
        webpage_html,
        UNWANTED_WEB_WORDS,
    )

    log("Cleaned webpage text:")
    log(webpage_text[:3000])
    log("")

    log("Step 4: Summarizing job posting...")
    job_information = summarize_job_posting(
        webpage_text=webpage_text,
        model=model,
    )

    log("Job information:")
    log(json.dumps(
        job_information,
        indent=2,
        ensure_ascii=False,
    ))
    log("")

    # Important: convert dict to string before sending to resume agents
    job_posting_text = json.dumps(
        job_information,
        indent=2,
        ensure_ascii=False,
    )

    log("Step 5: Loading master resume...")
    master_resume_text = load_resume(master_resume_path)

    if not master_resume_text.strip():
        raise ValueError("Master resume text is empty.")

    log("")

    log("step 5.1: Summarizing master resume for job...")
    resume_brief = summarize_resume_for_job(
    master_resume_text=master_resume_text,
    job_posting_text=job_posting_text,
    model=model,)
    
    master_resume_text=resume_brief

    log("")

    log("Step 6: Generating headline...")

    resume_data["headline"] = generate_headline_section(
        master_resume_text=master_resume_text,
        job_posting_text=job_posting_text,
        model=model,
    )

    log("Headline:")
    log(resume_data["headline"])
    log("")

    log("Step 7: Generating professional summary...")
    resume_data["professional_summary"] = generate_professional_summary(
        master_resume_text=master_resume_text,
        job_posting_text=job_posting_text,
        model=model,
    )

    log("Professional summary:")
    log(resume_data["professional_summary"])
    log("")

    log("Step 8: Generating experience section...")
    experience_result = generate_experience_section(
        master_resume_text=master_resume_text,
        job_posting_text=job_posting_text,
        model=model,
    )

    resume_data["experience"] = experience_result["experience"]

    log("Experience:")
    log(json.dumps(
        resume_data["experience"],
        indent=2,
        ensure_ascii=False,
    ))
    log("")

    log("Step 9: Generating skills section...")
    resume_data["skills"] = generate_skills_section(
        master_resume_text=master_resume_text,
        job_posting_text=job_posting_text,
        model=model,
    )

    log("Skills:")
    log(json.dumps(
        resume_data["skills"],
        indent=2,
        ensure_ascii=False,
    ))
    log("")

    log("Step 10: Generating projects section...")
    projects_result = generate_projects_section(
        master_resume_text=master_resume_text,
        job_posting_text=job_posting_text,
        model=model,
    )

    resume_data["projects"] = projects_result["projects"]

    log("Projects:")
    log(json.dumps(
        resume_data["projects"],
        indent=2,
        ensure_ascii=False,
    ))
    log("")

    log("Step 11: Generating PDF...")
    output_path = generate_resume_pdf(
        resume_data=resume_data,
        output_filename=output_filename,
    )

    log(f"Resume PDF created successfully:\n{output_path}")

    return str(output_path)


def main():
    print(" This script is intended to be run as part of a PyQt6 GUI application.")
    



if __name__ == "__main__":
    main()