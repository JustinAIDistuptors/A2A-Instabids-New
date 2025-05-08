import { StreamingTextResponse, Message as VercelChatMessage } from 'ai';
import { NextRequest } from 'next/server';

// IMPORTANT! Set the runtime to edge
export const runtime = 'edge';

export async function POST(req: NextRequest) {
  try {
    const { messages } = await req.json();

    // For now, we'll just log the messages and stream back a simple response.
    // In a real application, you would send messages to your AI model here.
    console.log('Received messages:', messages);

    // Example: Stream a simple "Hello, world!" response
    const stream = new ReadableStream({
      async start(controller) {
        const text = "Hello, world! This is a streamed response from the Next.js API route.";
        for (const char of text) {
          controller.enqueue(new TextEncoder().encode(char));
          await new Promise(resolve => setTimeout(resolve, 50)); // Simulate delay
        }
        controller.close();
      },
    });

    return new StreamingTextResponse(stream);

  } catch (error) {
    console.error('[CHAT_API_ERROR]', error);
    return new Response('Error processing chat request', { status: 500 });
  }
}