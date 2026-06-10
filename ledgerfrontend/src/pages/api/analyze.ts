import type { APIRoute } from 'astro';
import { GoogleGenAI } from '@google/genai';

export const POST: APIRoute = async ({ request }) => {
  try {
    const body = await request.json();
    const { groupName, groupType, budgetType, maxBudget, totalSpent, expenseSummary } = body;

    const apiKey = process.env.GEMINI_API_KEY;
    if (!apiKey) {
       return new Response(JSON.stringify({ text: "API Key Error: GEMINI_API_KEY is not defined on the server side. Please ensure the user secret is set in the panel." }), {
         status: 200, // Return friendly text to UI
         headers: { 'Content-Type': 'application/json' }
       });
    }

    const ai = new GoogleGenAI({ apiKey });

    const prompt = `
      Analyze the following spending data for a group budget named "${groupName}".
      Group Type: ${groupType}
      Budget Type: ${budgetType}
      Max Budget: ${maxBudget || 'No limit'}
      Total Spent in Current Period: ${totalSpent}
      
      Expenses:
      ${JSON.stringify(expenseSummary, null, 2)}
      
      Please provide:
      1. A summary of spending habits.
      2. Identification of any unusual or high spending categories.
      3. Practical suggestions for saving or better budget management.
      4. A brief outlook based on the current budget limit.
      
      Keep the tone helpful, professional, and encouraging. Use markdown for formatting.
    `;

    const response = await ai.models.generateContent({
      model: "gemini-2.5-flash",
      contents: [{ parts: [{ text: prompt }] }]
    });

    return new Response(JSON.stringify({ text: response.text || "Could not generate analysis." }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    });
  } catch (error: any) {
    console.error("API error during Gemini call:", error);
    return new Response(JSON.stringify({ text: `AI analysis error: ${error.message || String(error)}` }), {
      status: 200, // Safe recovery in UI
      headers: { 'Content-Type': 'application/json' }
    });
  }
};
export const ALL: APIRoute = () => {
  return new Response("Method not allowed", { status: 405 });
};
