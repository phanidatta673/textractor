import json
import os
import urllib.request

SPRITES_TOKEN = os.environ.get('SPRITES_TOKEN')
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')
REPO_URL = os.environ.get('REPO_URL')

def handler(event, context):
    try:
        body = json.loads(event.get('body', '{}'))
        action = body.get('action')
        issue = body.get('issue')

        if action == 'opened' and issue:
            issue_number = issue.get('number')
            issue_title = issue.get('title')
            print(f"New issue: {issue_title}")
            
            # 1. Launch Sprite Sandbox
            sprite_name = f"textractor-fix-{issue_number}"
            url = f"https://api.sprites.dev/v1/sprites/{sprite_name}"
            
            data = json.dumps({}).encode('utf-8')
            req = urllib.request.Request(
                url, 
                data=data, 
                headers={
                    'Authorization': f'Bearer {SPRITES_TOKEN}',
                    'Content-Type': 'application/json'
                },
                method='PUT'
            )

            try:
                with urllib.request.urlopen(req) as response:
                    res_body = response.read().decode('utf-8')
                    print(f"Sprite launched successfully: {res_body}")
            except urllib.error.HTTPError as e:
                print(f"Failed to launch Sprite: {e.read().decode('utf-8')}")
                raise

            # 2. Trigger Gemini CLI inside Sprite (Placeholder)
            # This would require a Sprite execution API call
            
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'OK'})
        }
    except Exception as e:
        print(f"Error handling GitHub issue: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
