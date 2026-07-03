CAREER_SITES = {
    "SaskTel": {
        "url": "https://jobs.sasktel.com/go/Current-Opportunities/2684517/",
        "method": "requests",
    },
    "FCC": {
        "url": "https://fccfac.wd3.myworkdayjobs.com/en-CA/careers-carrieres",
        "method": "playwright",
    },
    "SaskPower": {"url": "https://jobs.saskpower.com/search/?q=", "method": "requests"},
    "SaskEnergy": {
        "url": "https://saskenergy.wd10.myworkdayjobs.com/SaskEnergy",
        "method": "playwright",
    },
    "Government of Saskatchewan": {
        "url": "https://careers.saskatchewan.ca/#en/sites/CX_1/jobs?lastSelectedFacet=CATEGORIES&selectedCategoriesFacet=300000023968083",
        "method": "playwright",
    },
    "eHealth Saskatchewan": {
        "url": "https://www.ehealthsask.ca/Careers/Pages/default.aspx",
        "method": "playwright",
    },
    "WCB Saskatchewan": {
        "url": "https://fa-ewle-saasfaprod1.fa.ocs.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/jobs",
        "method": "playwright",
    },
    "University of Regina": {
        "url": "https://urcareers.uregina.ca/postings/search?utf8=%E2%9C%93&query=&query_v0_posted_at_date=&435=&225=&query_position_type_id%5B%5D=1&commit=Search",
        "method": "requests",
    },  "Saskatchewan Health Authority": {
        "url": "https://emqk.fa.ca3.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/jobs",
        "method": "playwright",
    },
    "Alberta Blue Cross": {
        "url": "https://abbluecross.wd3.myworkdayjobs.com/careers",
        "method": "playwright",
    },
    "Enbridge": {
        "url": "https://enbridge.wd3.myworkdayjobs.com/enbridge_careers",
        "method": "playwright",
    },
    "Canadian Natural Resources": {
        "url": "https://ehaa.fa.ca2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CNRL-Professional/jobs",
        "method": "playwright",
    },
    "Stantec": {
        "url": "https://stantec.jobs/jobs/",
        "method": "playwright",
    },
    "Affinity Credit Union": {
        "url": "https://jobs.dayforcehcm.com/affinity/CANDIDATEPORTAL",
        "method": "playwright",
    },
     "CAASK": {
        "url": "https://caask.ca/about-caa/careers",
        "method": "requests",
    }
}

UNWANTED_JOB_KEYWORDS = [
    "nurse",
    "physician",
    "doctor",
    "pharmacist",
    "dentist",
    "sales",
    "retail",
    "cashier",
    "cook",
    "chef",
    "server",
    "bartender",
    "cleaner",
    "labourer",
    "warehouse",
    "driver",
    "security guard",
    "customer service representative",
    "customer support",
    "receptionist",
    "administrative assistant",
    "marketing",
    "communications",
    "hr",
    "human resources",
    "recruiter",
    "finance",
    "accountant",
    "legal",
]

UNWANTED_WEB_WORDS = [
    # Cookie banners
        "cookie",
        "cookie consent",
        "accept all cookies",
        "modify cookie preferences",
        "privacy",
        "privacy policy",
        "cookie policy",
        # Website navigation
        "login",
        "log in",
        "create account",
        "sign in",
        "sign up",
        "search by keyword",
        "search by location",
        "clear",
        "create alert",
        "career alerts",
        "be in the know",
        # Footer
        "legal",
        "terms",
        "contact us",
        "all rights reserved",
        "copyright",
        "opens in a new tab",
        "follow us",
        "linkedin",
        "youtube",
        "facebook",
        "twitter",
        # Accessibility
        "skip to main content",
        # Generic website text
        "helpful links",
        "other links",
        "required cookies",
        "functional cookies",
        "enabled",
        "provider",
        "description",
        "confirm my choices",
    ]