import { S3Client, PutObjectCommand } from "@aws-sdk/client-s3";
import { getSignedUrl } from "@aws-sdk/s3-request-presigner";
import { v4 as uuidv4 } from "uuid";
import { APIGatewayProxyEvent, APIGatewayProxyResult } from "aws-lambda";

const s3 = new S3Client({});
const BUCKET_NAME = process.env.BUCKET_NAME!;

export const handler = async (event: APIGatewayProxyEvent): Promise<APIGatewayProxyResult> => {
    try {
        const body = JSON.parse(event.body || "{}");
        const { filename, contentType } = body;

        if (!filename || !contentType) {
            return {
                statusCode: 400,
                body: JSON.stringify({ error: "Missing filename or contentType" }),
            };
        }

        const fileId = uuidv4();
        const extension = filename.split(".").pop();
        const key = `uploads/${fileId}.${extension}`;

        const command = new PutObjectCommand({
            Bucket: BUCKET_NAME,
            Key: key,
            ContentType: contentType,
        });

        const uploadUrl = await getSignedUrl(s3, command, { expiresIn: 3600 });

        return {
            statusCode: 200,
            headers: { "Access-Control-Allow-Origin": "*" },
            body: JSON.stringify({ uploadUrl, fileId, key }),
        };
    } catch (error: any) {
        console.error("Error generating presigned URL:", error);
        return {
            statusCode: 500,
            headers: { "Access-Control-Allow-Origin": "*" },
            body: JSON.stringify({ error: error.message }),
        };
    }
};
