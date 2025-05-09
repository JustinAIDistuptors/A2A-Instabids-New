// src/app/api/chat/route.ts
import OpenAI from 'openai';
import { OpenAIStream, StreamingTextResponse } from 'ai';

// IMPORTANT: Replace with your actual OpenAI API key
// Ensure this is set in your environment variables and not hardcoded!
const OPENAI_API_KEY = process.env.OPENAI_API_KEY;

if (!OPENAI_API_KEY) {
  // In a real app, you might want to return an error response or have a fallback
  // For now, we'll log and the app might not function as expected if this key is missing.
  console.warn('Missing OPENAI_API_KEY environment variable. Chat API may not function.');
  // Depending on strictness, you might throw new Error('Missing OPENAI_API_KEY environment variable');
}

// Create an OpenAI API client (that's edge friendly!)
const openai = new OpenAI({
  apiKey: OPENAI_API_KEY || '',
});

export const runtime = 'edge'; // Use edge runtime for Vercel AI SDK

export async function POST(req: Request) {
  try {
    // Handle cases where OPENAI_API_KEY might be missing more gracefully at runtime
    if (!OPENAI_API_KEY) {
      return new Response(JSON.stringify({ error: 'Server configuration error: Missing API key.' }), {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    // Extract the `messages` from the body of the request
    const { messages } = await req.json();

    // Request the OpenAI API for a streaming chat completion.
    const response = await openai.chat.completions.create({
      model: 'gpt-3.5-turbo',
      stream: true,
      messages: messages,
    });

    // Convert the response into a friendly text-stream
    const stream = OpenAIStream(response);
    // Respond with the stream
    return new StreamingTextResponse(stream);

  } catch (error) {
    console.error('[API CHAT POST Error]', error);
    const errorMessage = error instanceof Error ? error.message : 'An unknown error occurred';
    return new Response(JSON.stringify({ error: 'Failed to process chat request', details: errorMessage }), {
      status: 500,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  }
}
