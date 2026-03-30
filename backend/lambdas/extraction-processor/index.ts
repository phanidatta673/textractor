import { S3Client, GetObjectCommand } from "@aws-sdk/client-s3";
import { DynamoDBClient, UpdateItemCommand } from "@aws-sdk/client-dynamodb";
import { marshall } from "@aws-sdk/util-dynamodb";
import pdf from "pdf-parse";
import mammoth from "mammoth";
import JSZip from "jszip";
import { S3Event, Context } from "aws-lambda";

const s3 = new S3Client({});
const dynamodb = new DynamoDBClient({});

const TABLE_NAME = process.env.TABLE_NAME || "Extractions";

/**
 * Text Extraction Logic for ExtractionProcessor Lambda
 */
export const handler = async (event: any, context: Context) => {
    // The event could be from S3 or passed from StartExtraction
    const records = event.Records || [];
    
    for (const record of records) {
        const bucket = record.s3.bucket.name;
        const key = decodeURIComponent(record.s3.object.key.replace(/\+/g, " "));
        const fileId = key.split("/").pop()?.split(".")[0] || key;

        try {
            await updateStatus(fileId, "PROCESSING");

            const getObjectParams = { Bucket: bucket, Key: key };
            const response = await s3.send(new GetObjectCommand(getObjectParams));
            const body = await response.Body?.transformToByteArray();

            if (!body) throw new Error("Empty file body");

            const extension = key.split(".").pop()?.toLowerCase();
            const extractedText = await extractText(body, extension);

            await updateStatus(fileId, "COMPLETED", extractedText);

        } catch (error: any) {
            console.error("Extraction error:", error);
            await updateStatus(fileId, "FAILED", undefined, error.message);
        }
    }
};

async function extractText(buffer: Uint8Array, extension?: string): Promise<string> {
    if (extension === "pdf") {
        const data = await pdf(Buffer.from(buffer));
        return data.text;
    } else if (extension === "docx") {
        const result = await mammoth.extractRawText({ buffer: Buffer.from(buffer) });
        return result.value;
    } else if (extension === "txt") {
        return Buffer.from(buffer).toString("utf-8");
    } else if (extension === "zip") {
        const zip = await JSZip.loadAsync(buffer);
        let combinedText = "";
        for (const [filename, file] of Object.entries(zip.files)) {
            if (file.dir) continue;
            const fileExtension = filename.split(".").pop()?.toLowerCase();
            const fileData = await file.async("uint8array");
            try {
                const text = await extractText(fileData, fileExtension);
                combinedText += `\n--- File: ${filename} ---\n${text}\n`;
            } catch (err) {
                console.warn(`Skipping file ${filename} in zip: Unsupported or corrupted`);
            }
        }
        return combinedText;
    } else {
        throw new Error(`Unsupported file type: ${extension}`);
    }
}

async function updateStatus(fileId: string, status: string, content?: string, error?: string) {
    const ttl = Math.floor(Date.now() / 1000) + 600; // 10 minutes from now
    const params = {
        TableName: TABLE_NAME,
        Key: marshall({ fileId }),
        UpdateExpression: "SET #s = :s, #t = :t, #ttl = :ttl" + (content ? ", #c = :c" : "") + (error ? ", #e = :e" : ""),
        ExpressionAttributeNames: {
            "#s": "status",
            "#t": "updatedAt",
            "#ttl": "ttl",
            ...(content && { "#c": "content" }),
            ...(error && { "#e": "error" }),
        },
        ExpressionAttributeValues: marshall({
            ":s": status,
            ":t": new Date().toISOString(),
            ":ttl": ttl,
            ...(content && { ":c": content }),
            ...(error && { ":e": error }),
        }),
    };

    await dynamodb.send(new UpdateItemCommand(params));
}
