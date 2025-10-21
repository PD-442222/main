# SAP Purchase Requisition MCP Server

This repository packages a beginner-friendly [Model Context Protocol (MCP)](https://spec.modelcontextprotocol.io/) server that wraps the SAP Purchase Requisition sandbox API. It runs on free hosting such as Hugging Face Spaces and can be driven by OpenAI AgentKit or a small helper script. All configuration happens through environment variables so you do not need to edit the Python source files.

## TL;DR for non-developers

1. **Get your SAP sandbox API key.** It is free and required for every request.
2. **Deploy the server to Hugging Face Spaces** by uploading the files in this repository.
3. **Set the `SAP_API_KEY` secret** in the Space settings and wait for the build to finish.
4. **Test the running server** by visiting the `/docs` page in the Space or by running the included `client_example.py` script from anywhere (for example Google Colab).

The sections below expand each step in detail and include copy‑paste commands.

## Step 1 – collect the required accounts and keys

- **SAP sandbox API key:**
  1. Sign in (or create an account) at [SAP API Business Hub](https://api.sap.com/).
  2. Open the [Purchase Requisition API page](https://api.sap.com/api/API_PURCHASEREQ_2_SRV/overview) and click **Try Out**.
  3. Generate a sandbox API key and copy it. The key looks like a long string of letters and numbers.
- **Optional – ngrok token:** if you plan to run the server temporarily from Google Colab, grab your free auth token from the [ngrok dashboard](https://dashboard.ngrok.com/get-started/your-authtoken).

You do **not** need any paid services or software installed locally.

## Step 2 – deploy on Hugging Face Spaces (recommended)

1. Create a new Space at <https://huggingface.co/spaces>.
2. Choose the **FastAPI** template, give the Space a name (e.g. `sap-pr-mcp`), and keep it **Public** so AgentKit can reach it.
3. Upload the following files from this repository:
   - `app.py`
   - `requirements.txt`
   - the entire `model_context_protocol/` folder (drag the folder or upload it as a `.zip` and extract it in the UI).
4. Open the **Settings → Variables and secrets** panel in the Space and add a new secret:
   - Name: `SAP_API_KEY`
   - Value: *paste the API key you collected in Step&nbsp;1*
5. Press **Restart** if the Space does not rebuild automatically. The build log (accessible from the Space page) should end with `Application startup complete.`

### How to confirm the Space is working

- Visit `https://<your-space>.hf.space` — you should see `{"status": "ok", "mcp": "available"}`.
- Open `https://<your-space>.hf.space/docs` to access the interactive Swagger UI provided by FastAPI. Use the **GET /mcp/tools** entry to list available tools, then use **POST /mcp/tools/list_purchase_requisitions** with the example payload `{ "top": 5 }` to pull live data.
- For a command-line check (e.g. from Google Colab), run:

  ```bash
  python client_example.py --base-url https://<your-space>.hf.space --top 5
  ```

  The script prints the server health status, the discovered MCP tools, and the first few requisition items returned by SAP.

## Step 3 – optional Google Colab session (temporary server)

Use this option only if you want to experiment before deploying to Hugging Face. Each Colab runtime is temporary, so the server stops when the notebook is closed.

1. Start a new notebook at <https://colab.research.google.com/>.
2. Run the following cell to copy the project files into the notebook:

   ```python
   !git clone https://huggingface.co/spaces/<your-username>/<your-space> sap_mcp
   %cd sap_mcp
   ```

   Replace `<your-username>/<your-space>` with the path to the repository backing your Hugging Face Space. If you do not have a Space yet, you can clone this GitHub repository instead.
3. Install the dependencies and ngrok helper:

   ```python
   !pip install -r requirements.txt pyngrok
   ```

4. Configure secrets inside the notebook:

   ```python
   import os

   os.environ["SAP_API_KEY"] = "paste-your-sap-api-key-here"
   os.environ["NGROK_AUTH_TOKEN"] = "paste-your-ngrok-token-here"
   ```

5. Start the tunnel and launch the server:

   ```python
   from pyngrok import ngrok
   import subprocess

   public_url = ngrok.connect(8000, "http")
   print("Public MCP URL:", f"{public_url}/mcp")

   server = subprocess.Popen([
       "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"
   ])
   ```

   Keep the notebook running; Colab will stop the process if the cell is interrupted.
6. Use the printed URL with AgentKit or run `python client_example.py --base-url <public-url>` from another Colab notebook to test the deployment.

## Using the helper script for quick tests

`client_example.py` is included for users who prefer not to craft HTTP requests manually. It performs three checks:

1. Calls the root health endpoint.
2. Lists available MCP tools.
3. Invokes `list_purchase_requisitions` with a configurable `top` parameter (default `5`).

Example usage:

```bash
# Test a local server
python client_example.py

# Test a remote Hugging Face Space
python client_example.py --base-url https://<your-space>.hf.space --top 10
```

If you are running the command from a notebook, prefix it with `!`.

## Connecting from OpenAI AgentKit

AgentKit expects an MCP endpoint. Configure the tool like this:

```json
{
  "url": "https://<your-space>.hf.space/mcp",
  "capabilities": ["tools"],
  "name": "sap_purchase_requisitions"
}
```

AgentKit will call `GET /mcp/tools` to discover the `list_purchase_requisitions` tool and then `POST /mcp/tools/list_purchase_requisitions` to run it. The payload schema returned by the discovery endpoint matches the FastAPI parameters in `app.py`.

## Local development notes (optional)

- Python 3.9 or newer is recommended.
- Install dependencies with `pip install -r requirements.txt`.
- To run the server locally, execute `uvicorn app:app --host 0.0.0.0 --port 8000` and set `SAP_API_KEY` in your environment or an `.env` file.
- The SAP sandbox enforces rate limits; keep the `top` parameter modest.
- You can use the `$select` and `$filter` parameters to minimize payload size.
- Error messages from SAP are surfaced directly in the MCP tool response for easier debugging.

## Testing

For a lightweight syntax check, run:

```bash
python -m compileall app.py model_context_protocol client_example.py
```

## Troubleshooting redeployments

It is safe to rebuild or re-upload the project files whenever you want to "start over." A quick reset usually solves build
issues without touching any code:

1. **Force a Hugging Face rebuild:** Open your Space, click **Settings → Restart this Space**, and wait for the build log to
   show `Application startup complete.`
2. **Re-upload the files:** If you deleted or overwrote anything, download the latest ZIP of this repository from GitHub, then
   drag `app.py`, `requirements.txt`, `client_example.py`, and the `model_context_protocol` folder back into the Space’s **Files**
   tab. Hugging Face automatically restarts after uploads.
3. **Need a fresh Git commit?** Delete the old files in your fork (or create a new branch) and upload the same files again. A
   new commit with identical contents is perfectly fine if you just need to re-trigger a pull request or rebuild pipeline.

These steps do not require any local tools—everything can be performed through the Hugging Face web interface.
