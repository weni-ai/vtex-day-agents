# Create Booth Map Tool - AWS Lambda Compatible

This tool creates visual route maps between booths at VTEX Day event. It has been updated to be compatible with AWS Lambda's read-only file system.

## Changes for AWS Lambda Compatibility

### Problem
AWS Lambda has a read-only file system (except for `/tmp`), which caused the error:
```
[ERROR] OSError: [Errno 30] Read-only file system: 'route_map.png'
```

### Solution
The tool now:
1. Generates the image in memory using `io.BytesIO` instead of saving to disk
2. Uploads the image to Imgur (a free image hosting service)
3. Returns the public URL of the uploaded image

## Image Hosting

The tool uses **Imgur** for temporary image hosting because:
- Free API with anonymous uploads
- No account required for basic usage
- Images are publicly accessible via URL
- Perfect for temporary route maps

## Credentials

### Using Custom Imgur Client ID (Optional)
1. Register at https://api.imgur.com/oauth2/addclient
2. Get your Client ID
3. Add to your agent definition:
```yaml
booth_location_agent:
    credentials:
        imgur_client_id:
            label: "Imgur Client ID"
            placeholder: "Enter your Imgur Client ID"
```

### Default Behavior
If no credential is provided, the tool uses a default anonymous Client ID that works for basic uploads.

## Local Testing

Create a `.env` file:
```
imgur_client_id=your_client_id_here
```

Then run:
```bash
weni run agent_definition.yaml booth_location_agent create_booth_map
```

## Response Format

The tool now returns:
```json
{
    "image_url": "https://i.imgur.com/xxxxx.png",
    "path_names": ["Starting Booth", "Destination Booth"],
    "message": "Route map from X to Y has been generated successfully!"
}
```

## Error Handling

If the upload fails, the tool returns:
```json
{
    "error": "Error message",
    "path_names": ["Starting Booth", "Destination Booth"],
    "message": "Failed to upload the route map image"
}
``` 