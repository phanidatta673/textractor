import { LambdaClient, InvokeCommand } from "@aws-sdk/client-lambda";
import { DynamoDBClient, PutItemCommand } from "@aws-sdk/client-dynamodb";
import { marshall } from "@aws-sdk/util-dynamodb";
import { APIGatewayProxyEvent, APIGatewayProxyResult } from "aws-lambda";

const lambda = new LambdaClient({});
const dynamodb = new DynamoDBClient({});

const TABLE_NAME = process.env.TABLE_NAME!;
const PROCESSOR_LAMBDA = process.env.PROCESSOR_LAMBDA!;

export const handler = async (event: APIGatewayProxyEvent): Promise<APIGatewayProxyResult> => {
    try {
        const body = JSON.parse(event.body || "{}");
        const { fileId, key, bucket } = body;

        if (!fileId || !key || !bucket) {
            return {
                statusCode: 400,
                body: JSON.stringify({ error: "Missing fileId, key, or bucket" }),
            };
        }

        // 1. Initial status update to DynamoDB
        const ttl = Math.floor(Date.now() / 1000) + 600; // 10 minutes
        await dynamodb.send(new PutItemCommand({
            TableName: TABLE_NAME,
            Item: marshall({
                fileId,
                status: "PENDING",
                updatedAt: new Date().toISOString(),
                ttl
            }),
        }));

        // 2. Asynchronously invoke ExtractionProcessor
        const payload = {
            Records: [{
                s3: {
                    bucket: { name: bucket },
                    object: { key }
                }
            }]
        };

        await lambda.send(new InvokeCommand({
            FunctionName: PROCESSOR_LAMBDA,
            InvocationType: "Event",
            Payload: Buffer.from(JSON.stringify(payload)),
        }));

        return {
            statusCode: 200,
            headers: { "Access-Control-Allow-Origin": "*" },
            body: JSON.stringify({ message: "Extraction started", fileId }),
        };
    } catch (error: any) {
        console.error("Error starting extraction:", error);
        return {
            statusCode: 500,
            headers: { "Access-Control-Allow-Origin": "*" },
            body: JSON.stringify({ error: error.message }),
        };
    }
};
