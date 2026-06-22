import json
from typing import List, Dict, Any
from google import genai

def handle_chat_query(client: genai.Client, query: str, all_startups: List[Dict[str, Any]]) -> str:
    """
    Handle natural language query about the startups database by converting the list
    of startups into a context string for Gemini 2.5 Flash.
    """
    try:
        # Convert dataset to compact JSON string
        startups_json = json.dumps(all_startups, indent=2)
        
        prompt = f"""
You are the interactive AgriScout AI Assistant. Your goal is to help agriculture investors, VCs, and researchers analyze and find insights about tracked AgTech startups in their database.

Below is the complete dataset of all tracked startups currently stored in our Excel database:

Dataset:
{startups_json}

User Query: "{query}"

Answer the user's query accurately using ONLY the dataset provided above.
Provide clear answers:
- If they ask to list companies by a filter (e.g. 'Show AgTech startups funded in 2026', 'which startups are from Finland?'), list them in a bulleted list or markdown table.
- If they ask for stats (e.g. 'how many vertical farming startups do we have?'), give counts.
- Explain your reasoning if needed, but keep the focus on the data.
- If no companies match the filter, explain that politely.

Format your entire response in beautiful Markdown, utilizing headers, bold text, lists, and tables for high readability.
"""
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        
        if response.text:
            return response.text
        return "Unable to generate a response from the AI assistant."
        
    except Exception as e:
        print(f"Error in chat assistant query: {e}")
        return f"An error occurred while communicating with the AI Chat Assistant: {str(e)}"
