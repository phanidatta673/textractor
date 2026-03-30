import { DynamoDBClient, GetItemCommand } from "@aws-sdk/client-dynamodb";
import { unmarshall, marshall } from "@aws-sdk/util-dynamodb";
import { APIGatewayProxyEvent, APIGatewayProxyResult } from "aws-lambda";

const dynamodb = new DynamoDBClient({});
const TABLE_NAME = process.env.TABLE_NAME!;

export const handler = async (event: APIGatewayProxyEvent): Promise<APIGatewayProxyResult> => {
    try {
        const fileId = event.pathParameters?.fileId;

        if (!fileId) {
            return {
                statusCode: 400,
                body: JSON.stringify({ error: "Missing fileId" }),
            };
        }

        const command = new GetItemCommand({
            TableName: TABLE_NAME,
            Key: marshall({ fileId }),
        });

        const { Item } = await dynamodb.send(command);

        if (!Item) {
            return {
                statusCode: 404,
                body: JSON.stringify({ error: "Record not found" }),
            };
        }

        const data = unmarshall(Item);

        return {
            statusCode: 200,
            headers: { "Access-Control-Allow-Origin": "*" },
            body: JSON.stringify(data),
        };
    } catch (error: any) {
        console.error("Error getting status:", error);
        return {
            statusCode: 500,
            headers: { "Access-Control-Allow-Origin": "*" },
            body: JSON.stringify({ error: error.message }),
        };
    }
};
