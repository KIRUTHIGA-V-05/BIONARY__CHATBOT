import express from "express";
import { neon } from "@neondatabase/serverless";
import { GoogleGenerativeAI } from "@google/generative-ai";
import dotenv from "dotenv";

dotenv.config();
const router = express.Router();

const sql = neon(process.env.DATABASE_URL);
const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);
const model = genAI.getGenerativeModel({ model: "gemini-pro" });

router.post("/query", async (req, res) => {
  try {
    const { query } = req.body;

    // Step 1: Use Gemini to extract event name + requested attributes
    const intentPrompt = `
You are an intent extraction system. 
Return a JSON only. No other text.

Extract the event name and what attributes the user specifically wants.
Attributes include: "name", "domain", "date", "time", "venue", "details".
If user wants everything, set ["all"].

Question: "${query}"

JSON format:
{
  "event": "<event name or null>",
  "attributes_requested": ["attribute1", "attribute2"]
}
`;

    const intentResp = await model.generateContent(intentPrompt);
    const intentText = intentResp.response.text().trim();

    let intent;
    try {
      intent = JSON.parse(intentText);
    } catch {
      intent = { event: null, attributes_requested: ["all"] };
    }

    const { event, attributes_requested } = intent;

    if (!event) {
      return res.json({ answer: "Could not identify event name ❓" });
    }

    // Step 2: Retrieve the event by name (exact match)
    const result = await sql`
      SELECT * FROM events
      WHERE LOWER(name) LIKE LOWER(${`%${event}%`})
      LIMIT 1;
    `;

    if (result.length === 0) {
      return res.json({ answer: "Event not found in database ❌" });
    }

    const ev = result[0];

    // Step 3: Decide what fields to return based on attributes_requested
    let answer = "";

    if (attributes_requested.includes("all")) {
      answer = `
Name: ${ev.name}
Domain: ${ev.domain}
Date: ${ev.date}
Time: ${ev.time}
Venue: ${ev.venue}
Details: ${ev.details}
`;
    } else {
      const fieldMap = {
        name: `Name: ${ev.name}`,
        domain: `Domain: ${ev.domain}`,
        date: `Date: ${ev.date}`,
        time: `Time: ${ev.time}`,
        venue: `Venue: ${ev.venue}`,
        details: `Details: ${ev.details}`
      };

      attributes_requested.forEach(attr => {
        if (fieldMap[attr]) answer += `${fieldMap[attr]}\n`;
      });

      if (answer.trim() === "") {
        // fallback if LLM fails attribute extraction
        answer = `
Name: ${ev.name}
Domain: ${ev.domain}
Date: ${ev.date}
Time: ${ev.time}
Venue: ${ev.venue}
Details: ${ev.details}
`;
      }
    }

    res.json({ answer: answer.trim() });

  } catch (error) {
    console.error(error);
    res.status(500).json({ error: "Internal Server Error ❌" });
  }
});

export default router;
