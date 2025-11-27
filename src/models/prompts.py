VLM_ANALYSIS_PROMPT = """Analyze this image and respond ONLY with valid JSON. Do not include any text before or after the JSON.

Required JSON format (strict):
{
    "type": "object" or "paper" or "unknown",
    "count": <number> (0 if not applicable),
    "description": "<single-sentence summary>",
    "text_content": "<extracted text>" or null
}

Rules:
1. The response must be valid JSON only, no markdown, no code blocks, no explanations
2. "type" must be exactly "object", "paper", or "unknown"
3. "count" must be a number (0 for documents or if no objects detected)
4. "description" must be a string (empty string "" if not applicable)
5. "text_content" must be a string or null (null for object images, string for documents)
6. **FIRST, check if it's a document/paper (PRIORITY):**
   - If the image contains text, labels, forms, documents, product labels, or any written/printed content
   - If you see structured information like "Commission", "Mat no", "Description", or similar labels
   - If it's a paper document, label, or form → Set "type": "paper"
   - Extract ONLY these three specific fields:
     * The word/value directly below "Commission" label
     * The number directly below "Mat no" label
     * The two sentences directly below "Description" label
     * Extract ONLY these three pieces of information, nothing else
     * Format: "Commission: <value>\\nMat no: <number>\\nDescription: <sentence1> <sentence2>"
7. If it contains physical objects (not documents), provide count and description
   - **CRITICAL FOR SPROCKETS**: When sprockets are detected, provide a comprehensive and detailed description:
     * **Tooth Count**: Count the exact number of teeth visible (e.g., 36 teeth = sprocket_z36, 40 teeth = sprocket_z40, 48 teeth = sprocket_z48)
     * **Physical Dimensions**: Estimate or identify diameter, thickness, and overall size
     * **Material & Surface**: Describe material (steel, aluminum, plastic) and surface finish (chrome, painted, raw metal, etc.)
     * **Markings & Labels**: Read any engraved, printed, or stamped markings, part numbers, brand names, or specifications
     * **Design Features**: Note any distinguishing features like hub type, keyway, mounting holes, or special configurations
     * **Condition**: Describe visible condition (new, used, worn, damaged, etc.)
     * **Format**: Include the specific type name (e.g., "sprocket_z36") and provide detailed characteristics in the description
     * **Example**: "Five sprocket_z36 components, approximately 50mm diameter, steel material with chrome finish, DIN standard markings visible, appears to be in good condition"
     * If specific type cannot be determined, provide as much detail as possible about tooth count, size, material, and any visible markings
8. If YOLO detected no objects AND it's NOT a document, carefully analyze the image:
   - Count all visible objects in the image
   - Provide detailed physical characteristics: shape, color, size, material, purpose, distinguishing features
   - Describe what you see as accurately as possible
   - Set "type": "object" if objects are visible, or "unknown" if unclear
9. If the image type cannot be clearly determined (neither object nor paper), use "unknown" type:
   - Set "type": "unknown"
   - Provide a detailed description of what you see in the image
   - Include physical characteristics, shape, color, size, material, purpose, or any distinguishing features
   - The description should be comprehensive enough to help identify or register this as a new object
10. When hints are provided, use them to refine the count and description, but document detection takes priority
11. **CRITICAL**: Analyze the actual image content. Do NOT copy example responses. Generate a unique description based on what you actually see in the image."""
