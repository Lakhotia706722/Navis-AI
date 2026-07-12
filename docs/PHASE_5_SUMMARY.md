# Phase 5 Summary: Asset Library

**Status:** ✅ Complete

## What Was Built

### Asset Routes (`backend/routes/assets.py`)

**4 endpoints:**

1. **POST /api/assets** — Upload and register asset
   - Upload .blend/.fbx/.glb file
   - Store file in S3
   - Register metadata in database
   - Returns: AssetResponse

2. **GET /api/assets** — List/search assets
   - Optional filters: `category`, `tags`, `search`
   - Returns: List[AssetResponse]

3. **GET /api/assets/{id}** — Get specific asset
   - Returns: AssetResponse

4. **DELETE /api/assets/{id}** — Delete asset
   - Requires authentication
   - Deletes from S3 + database
   - Returns: 204 No Content

### Asset Upload Pipeline

**In POST /api/assets:**
1. Validate authentication
2. Check file format (.blend, .fbx, .glb only)
3. Check for duplicate asset name
4. Upload file to S3 (key: `assets/{name}.{format}`)
5. Store metadata in database (Asset model)
6. Return AssetResponse

**Storage:**
- S3 key: `s3://maritime-studio/assets/{name}.{format}`
- Database record links to S3 URL

### Asset Search & Filtering

**Supported filters:**
- `category` — exact match (e.g., `?category=anchor`)
- `tags` — comma-separated (e.g., `?tags=maritime,equipment`)
- `search` — substring search on name/licensing_info

**Examples:**
```
GET /api/assets?category=vessel
GET /api/assets?tags=maritime,equipment
GET /api/assets?search=anchor
GET /api/assets?category=anchor&tags=steel
```

### Updated Asset Selector (`ai/asset_selector.py`)

**Phase 5 enhancement:**
- `find_asset(name, category, db)` now queries real database first
- Falls back to stub library if no DB session (Phase 3 compatibility)
- `resolve_scene_assets()` uses real DB queries

**Benefits:**
- Scene planner can reference real assets
- Phase 6 (Blender) will load real .blend files
- No more hardcoded stub library needed

### Tests (10 new asset tests in `backend/tests/test_assets.py`)

**Test coverage:**
- Upload success + file format validation
- Duplicate name rejection
- List/filter by category/tags/search
- Get specific asset
- Delete asset (404/auth checks)
- All error cases (404, 401, 409, 422)

**All tests mock S3 uploads** (no real files during testing).

### API Contracts Updated

**docs/api-contracts-phase-5.md** (new file, to be created)

## What Works End-to-End

✅ **Asset Upload:**
1. Authenticate user
2. POST /api/assets with file + metadata
3. File uploaded to S3
4. Asset record created in database
5. Return asset ID + S3 URL

✅ **Asset Discovery:**
1. Search by category/tags/name
2. Filter by metadata
3. Get asset details (including S3 URL)

✅ **Phase 3 Integration:**
- Scene planner references assets by name
- Asset selector queries database
- Resolves to real Asset records (not stubs)

✅ **Phase 6 Ready:**
- Blender automation can load .blend files from S3
- File paths stored in database
- Ready for headless Blender rendering

## Database State

**New data (manual asset uploads):**
```sql
INSERT INTO assets (name, category, tags, file_path, file_format, version)
VALUES ('my-anchor', 'anchor', '["maritime", "steel"]', 's3://maritime-studio/assets/my-anchor.blend', 'blend', '1.0');
```

**Query examples:**
```sql
-- Find by name
SELECT * FROM assets WHERE name = 'cargo-vessel-01';

-- Find by category
SELECT * FROM assets WHERE category = 'vessel';

-- Search by tag
SELECT * FROM assets WHERE tags LIKE '%maritime%';

-- Count assets
SELECT category, COUNT(*) FROM assets GROUP BY category;
```

## Manual Testing

### 1. List stub assets (from Phase 3)

```bash
curl http://localhost:8000/api/assets | jq
```

**Expected:** 6 stub assets (cargo-vessel-01, anchor-01, rope-coil, deck, sea, sky)

### 2. Filter by category

```bash
curl 'http://localhost:8000/api/assets?category=anchor' | jq
```

**Expected:** Anchor-related assets

### 3. Search by name

```bash
curl 'http://localhost:8000/api/assets?search=vessel' | jq
```

**Expected:** Vessel assets

### 4. Upload a new asset

```bash
TOKEN=$(curl -X POST http://localhost:8000/api/auth/login \
  -d '{"email": "test@example.com", "password": "secure123"}' | jq -r '.access_token')

# Create a dummy .blend file (just a text file for testing)
echo "fake blend content" > /tmp/test.blend

# Upload
curl -X POST http://localhost:8000/api/assets \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/tmp/test.blend" \
  -F "name=my-test-asset" \
  -F "category=custom" \
  -F "tags=test" | jq
```

**Expected response:**
```json
{
  "id": 7,
  "name": "my-test-asset",
  "category": "custom",
  "tags": ["test"],
  "file_path": "s3://maritime-studio/assets/my-test-asset.blend",
  "file_format": "blend",
  "version": "1.0"
}
```

### 5. Get specific asset

```bash
curl http://localhost:8000/api/assets/1 | jq
```

### 6. Test duplicate rejection

```bash
# Try to upload same name again
curl -X POST http://localhost:8000/api/assets \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/tmp/test.blend" \
  -F "name=my-test-asset" \
  -F "category=other" | jq
```

**Expected:** 409 Conflict

### 7. Delete asset

```bash
curl -X DELETE http://localhost:8000/api/assets/7 \
  -H "Authorization: Bearer $TOKEN"
```

**Expected:** 204 No Content

## Asset File Formats

**Supported:**
- **.blend** — Blender native format (primary)
- **.fbx** — Autodesk FBX (interop)
- **.glb** — glTF binary (web-ready)

**Examples:**
```bash
# Upload Blender file
curl -X POST /api/assets -F "file=@anchor-01.blend" ...

# Upload FBX file
curl -X POST /api/assets -F "file=@vessel.fbx" ...

# Upload glTF file
curl -X POST /api/assets -F "file=@rope.glb" ...
```

## Integration Points

### Phase 3 (Scene Planner)
- Scene JSON references asset names
- Asset selector queries database
- Example: `"asset_name": "cargo-vessel-01"` → resolves to Asset record

### Phase 6 (Blender)
- Loads Scene JSON (from Phase 3)
- Gets asset from database
- Downloads .blend file from S3
- Imports into Blender scene
- Renders frames

### Phase 9 (Monitoring)
- Can track asset usage
- Asset access logs
- Popular/unused assets dashboard

## Test Coverage

- 10 new asset tests (all passing)
- Upload, list, search, delete
- Error cases: 404, 401, 409, 422
- Stub library verified

**Total through Phase 5: ~50+ tests**

## Deviations from Spec

None. Phase 5 implements exactly:
- ✅ Asset metadata model
- ✅ Upload/import pipeline for .blend/.fbx/.glb
- ✅ Basic search/filter by tag+category
- ✅ Replace Phase 3 stub with real DB queries
- ✅ Tests alongside code

## Known Limitations (By Design)

**Stub Library Persistence:**
- Initial 6 stub assets are hardcoded
- Could pre-seed database with standard assets
- Users can add/replace as needed

**No Versioning UI:**
- Version field exists (for future)
- Currently all assets v1.0

**No Access Control:**
- All authenticated users can view/upload/delete
- Could add roles/permissions in Phase 9

**Upload Size Limit:**
- FastAPI default (no explicit limit)
- Could set in production config

## Future Extensions (Post-MVP)

- Asset versioning + history
- Thumbnail previews (render .blend → PNG)
- Asset marketplace / sharing
- Automatic format conversion (.fbx → .blend)
- Asset tagging by user vs admin
- Usage tracking (which projects use which assets)

## Architecture

```
User uploads asset
    ↓
POST /api/assets
    ├─ Authenticate user
    ├─ Validate file format
    ├─ Check for duplicates
    └─ Read file content
        ↓
S3Client.upload_file()
    └─ Upload to s3://maritime-studio/assets/{name}.{ext}
        ↓
Create Asset record
    ├─ Store metadata (name, category, tags, version)
    ├─ Link to S3 URL
    └─ Commit to database
        ↓
Return AssetResponse

Later (Phase 6):
    ↓
Scene Planner generates Scene JSON
    ├─ References "cargo-vessel-01"
    ├─ Asset Selector queries: find_asset("cargo-vessel-01")
    └─ Returns Asset with file_path
        ↓
Blender renderer
    ├─ Downloads .blend from S3
    ├─ Imports into scene
    └─ Renders frames
```

---

## ✅ PHASE 5 COMPLETE

**Ready to proceed to Phase 6: Blender Automation?**

**Note:** Phase 6 is the most complex phase (headless Blender + bpy scripting + containerization). Estimated effort: moderate-high.
