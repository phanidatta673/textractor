import { APIGatewayProxyEvent, APIGatewayProxyResult } from "aws-lambda";
import fetch from "node-fetch";

const SPRITES_TOKEN = process.env.SPRITES_TOKEN!;
const GITHUB_TOKEN = process.env.GITHUB_TOKEN!;
const REPO_URL = process.env.REPO_URL!;

export const handler = async (event: APIGatewayProxyEvent): Promise<APIGatewayProxyResult> => {
    try {
        const body = JSON.parse(event.body || "{}");
        const action = body.action;
        const issue = body.issue;

        if (action === "opened" && issue) {
            console.log(`New issue: ${issue.title}`);
            
            // 1. Launch Sprite Sandbox
            const spriteName = `textractor-fix-${issue.number}`;
            const launchResponse = await fetch(`https://api.sprites.dev/v1/sprites/${spriteName}`, {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${SPRITES_TOKEN}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    // Configuration can be added here
                })
            });

            if (!launchResponse.ok) {
                throw new Error(`Failed to launch Sprite: ${await launchResponse.text()}`);
            }

            console.log("Sprite launched successfully.");

            // 2. Trigger Gemini CLI inside Sprite (this requires Sprite CLI/API to run a command)
            // For now, we'll assume there's a way to run a command via API or we'll use SSH/Agent
            // Assuming Sprite API allows 'execute' or similar
            
            /*
            await fetch(`https://api.sprites.dev/v1/sprites/${spriteName}/execute`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${SPRITES_TOKEN}` },
                body: JSON.stringify({
                    command: `gemini -p "Fix issue #${issue.number}: ${issue.title}. ${issue.body}" --skip_dangerously --repo ${REPO_URL} --token ${GITHUB_TOKEN}`
                })
            });
            */
            
            // Note: The above is a placeholder for the actual Sprite command execution API
        }

        return {
            statusCode: 200,
            body: JSON.stringify({ message: "OK" }),
        };
    } catch (error: any) {
        console.error("Error handling GitHub issue:", error);
        return {
            statusCode: 500,
            body: JSON.stringify({ error: error.message }),
        };
    }
};
