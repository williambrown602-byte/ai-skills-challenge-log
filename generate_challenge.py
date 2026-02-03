import anthropic
import os
import re
from datetime import date

# Portfolio log file path
PORTFOLIO_LOG_PATH = "PortfolioLog.md"

# Template for portfolio log entries
PORTFOLIO_ENTRY_TEMPLATE = """# Daily AI Challenge – {date}

**Domain:** {domain}
**Tool Focus:** {tool_focus}
**Time Box:** {time_box}
**Status:** Pending

## Challenge Summary
{summary}

## Skills Trained
{skills}

## Deliverables
{deliverables}

---
"""

DAILY_CHALLENGE_PROMPT = """You are my daily AI skills coach.

Context:
- I am training to become a world-class AI power user and vibe coder.
- My primary tool is Claude Code, but I must also develop strong multi-tool skills.
- The goal is to build highly employable, high-value capabilities for future high-paid roles.
- Every challenge must combine:
  - technical implementation
  - real business value
  - practical workplace relevance
  - portfolio-ready outputs

TOOL BALANCE RULES

Across challenges:
- Around 70–80% should be primarily Claude Code focused
- Around 20–30% should require complementary tools such as:
  - APIs
  - Make.com / n8n
  - Spreadsheets
  - Databases (Supabase / SQLite)
  - BI tools
  - Simple web interfaces
  - Cloud services

This ensures I become versatile, not dependent on one environment.

CORE REQUIREMENTS

Each daily challenge must:
- Be solvable in 60–120 minutes
- Include a clear technical component
- Deliver measurable business value
- Train skills employers want now and in the future
- Produce an artefact I can showcase in interviews

SKILLS TO PRIORITISE

Over time ensure I develop:

Technical Skills:
- scripting and automation
- API integration
- data processing
- debugging
- AI agent creation
- workflow orchestration
- RAG / knowledge systems
- cloud tooling
- security awareness
- Git / version control

Business Skills:
- productivity improvement
- financial analysis
- reporting
- process optimisation
- decision support
- stakeholder communication
- ROI thinking

DOMAIN ROTATION

Rotate challenges across:
- Finance
- Operations
- HR
- Marketing
- Sales
- Consulting
- Project management
- Customer support
- Data analytics
- Internal productivity

REQUIRED OUTPUT FORMAT

You must generate the daily task using this exact structure:

DAILY PROFESSIONAL AI CHALLENGE – [Date]

🏢 Business Scenario
Describe a realistic workplace situation.

🎯 Objective
What I must achieve today.

🧩 Technical Requirement
Specify the core technical element.

TOOL FOCUS FOR TODAY:
State clearly one of the following:
- "Primarily Claude Code"
- "Mixed Tools (Claude Code + Integration)"
- "Business Tool Integration Focus"

📂 Inputs
Data or resources to assume.

📈 Business Deliverables
Exactly what I must produce.

🧠 Business Impact
Explain the value created for an employer.

🛠 Allowed Tools
List appropriate tools for this challenge.

⏱ Time Box
Target: 60–120 minutes

📁 Portfolio Artefact
What I should save to showcase.

🎓 Skills Trained
Key high-value skills.

🧪 Success Criteria
5 measurable checks.

🚀 Stretch Goals
Optional enhancements.

STRICT RULES FOR YOU
- Do NOT provide solutions
- Do NOT generate any code
- Only generate the challenge
- Ensure real business realism
- Always include a technical element
- Mix tool types over time
"""

EXTRACT_SUMMARY_PROMPT = """Extract the following information from this daily challenge and return it as a structured response.
Return ONLY the extracted values in this exact format (no extra text):

DOMAIN: [the business domain, e.g., Finance, Operations, HR]
TOOL_FOCUS: [e.g., Primarily Claude Code, Mixed Tools, Business Tool Integration Focus]
TIME_BOX: [e.g., 60-90 minutes]
SUMMARY: [1-2 sentence summary of the challenge objective]
SKILLS: [comma-separated list of 3-5 key skills]
DELIVERABLES: [comma-separated list of main deliverables]

Challenge to extract from:
{challenge}
"""

GENERATE_SAMPLE_DATA_PROMPT = """Based on this daily challenge, generate realistic sample data files that can be used to complete the challenge.

For each data file needed:
1. Determine the appropriate format (CSV, JSON, TXT, etc.)
2. Generate realistic, business-appropriate sample data
3. Include enough records to be useful (10-50 rows for CSVs, appropriate size for other formats)

Return the files in this EXACT format (one or more files):

===FILE: filename.extension===
[file contents here]
===END FILE===

===FILE: another_file.extension===
[file contents here]
===END FILE===

If the challenge doesn't require data files (e.g., it's about building a tool from scratch), return:
===NO DATA FILES NEEDED===

Challenge:
{challenge}
"""


def call_anthropic(prompt: str, model: str = "claude-sonnet-4-20250514") -> str:
    """Call the Anthropic API with a given prompt."""
    client = anthropic.Anthropic()
    response = client.messages.create(
        model=model,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text


def read_portfolio_log() -> str:
    """Read the existing portfolio log."""
    if os.path.exists(PORTFOLIO_LOG_PATH):
        with open(PORTFOLIO_LOG_PATH, 'r', encoding='utf-8') as f:
            return f.read()
    return ""


def build_prompt_with_context(today: str, previous_tasks: str) -> str:
    """Build the challenge prompt with context from previous tasks."""
    prompt = f"Generate the daily challenge for {today}.\n\n{DAILY_CHALLENGE_PROMPT}"

    if previous_tasks.strip():
        prompt += f"""

IMPORTANT - AVOID DUPLICATE CHALLENGES:
Below are summaries of previous challenges. Do NOT generate a challenge that shares BOTH the same domain AND similar skills as any previous challenge. Each new challenge must be meaningfully different.

Previous challenges:
{previous_tasks}
"""
    return prompt


def parse_extracted_summary(response: str) -> dict:
    """Parse the structured response from Claude into a dictionary."""
    result = {}
    for line in response.strip().split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            result[key.strip()] = value.strip()
    return result


def extract_and_append_summary(challenge: str, today: str):
    """Extract key info from the challenge and append to portfolio log."""
    extract_prompt = EXTRACT_SUMMARY_PROMPT.format(challenge=challenge)
    extracted = call_anthropic(extract_prompt)

    data = parse_extracted_summary(extracted)

    skills = data.get('SKILLS', '')
    skills_formatted = '\n'.join(f"- {s.strip()}" for s in skills.split(',') if s.strip())

    deliverables = data.get('DELIVERABLES', '')
    deliverables_formatted = '\n'.join(f"- {d.strip()}" for d in deliverables.split(',') if d.strip())

    entry = PORTFOLIO_ENTRY_TEMPLATE.format(
        date=today,
        domain=data.get('DOMAIN', 'Unknown'),
        tool_focus=data.get('TOOL_FOCUS', 'Unknown'),
        time_box=data.get('TIME_BOX', '60-120 minutes'),
        summary=data.get('SUMMARY', 'No summary available'),
        skills=skills_formatted,
        deliverables=deliverables_formatted
    )

    with open(PORTFOLIO_LOG_PATH, 'a', encoding='utf-8') as f:
        f.write(entry)

    print(f"Summary added to {PORTFOLIO_LOG_PATH}")


def save_challenge_to_file(challenge: str, today: str) -> str:
    """Save the full challenge to a markdown file."""
    os.makedirs("challenges", exist_ok=True)

    date_str = today.replace(" ", "_").replace(",", "")
    filename = f"challenge_{date_str}.md"
    filepath = os.path.join("challenges", filename)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(challenge)

    print(f"Challenge saved to: {filepath}")
    return filepath


def generate_sample_data(challenge: str, today: str) -> str:
    """Generate sample data files based on the challenge requirements."""
    date_folder = today.replace(" ", "_").replace(",", "")
    data_dir = os.path.join("challenge_data", date_folder)
    os.makedirs(data_dir, exist_ok=True)

    prompt = GENERATE_SAMPLE_DATA_PROMPT.format(challenge=challenge)
    response = call_anthropic(prompt)

    if "===NO DATA FILES NEEDED===" in response:
        print("No sample data files needed for this challenge")
        return data_dir

    file_pattern = r'===FILE: (.+?)===\n(.*?)===END FILE==='
    matches = re.findall(file_pattern, response, re.DOTALL)

    if not matches:
        print("Could not parse sample data from response")
        return data_dir

    files_created = []
    for filename, content in matches:
        filename = filename.strip()
        content = content.strip()
        filepath = os.path.join(data_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        files_created.append(filename)

    print(f"Sample data files created in: {data_dir}")
    for f in files_created:
        print(f"  - {f}")

    return data_dir


if __name__ == "__main__":
    # Read existing log
    previous_tasks = read_portfolio_log()

    # Generate challenge
    today = date.today().strftime("%B %d, %Y")
    prompt = build_prompt_with_context(today, previous_tasks)
    challenge = call_anthropic(prompt)

    # Print the challenge
    print("=" * 60)
    print(challenge)
    print("=" * 60)

    # Generate sample data
    generate_sample_data(challenge, today)

    # Save challenge to file
    save_challenge_to_file(challenge, today)

    # Extract summary and append to portfolio log
    extract_and_append_summary(challenge, today)

    print("\nDaily challenge generation complete!")
