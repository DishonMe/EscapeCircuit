# How to Run EscapeCircuit

## Initial Setup (First Time Only)

1. **Configure Frontend Environment:**
   Edit `apps/nextjs-app/.env` and set your Google Client ID:
   ```
   NEXT_PUBLIC_GOOGLE_CLIENT_ID=your_google_client_id_here
   ```
   
   To get your Google Client ID:
   - Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
   - Create an OAuth 2.0 Client ID for Web Application
   - Copy the Client ID and paste it in the `.env` file

2. **Install Python Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Initialize the Database:**
   ```bash
   python src/init_db.py
   python src/insert_riddles.py
   python src/seed_admin.py
   ```

## Running the Project

### Option 1: Automated (Recommended)
From the project root, run:
```bash
python init_env.py
```

This will:
- Read `NEXT_PUBLIC_GOOGLE_CLIENT_ID` from `apps/nextjs-app/.env`
- Use it for both frontend and backend automatically
- Start both servers concurrently on ports 8080 (backend) and 3000 (frontend)

### Option 2: Manual - Separate Terminals

**Terminal 1 (Backend):**
```bash
cd src
python -m uvicorn Backend.main:app --reload --host 127.0.0.1 --port 8080
```

**Terminal 2 (Frontend):**
```bash
cd apps/nextjs-app
npm install  # if not already done
npm run dev
```

## Access the Application

- Frontend: http://localhost:3000
- Backend API: http://localhost:8080

## Credentials

- **Admin Account:** username=`admin`, password=`password123`
- **Google OAuth:** Uses `NEXT_PUBLIC_GOOGLE_CLIENT_ID` from `apps/nextjs-app/.env`

## For Coworkers

Each person should:
1. Edit their own `apps/nextjs-app/.env` with their Google Client ID
2. Run `python init_env.py`
3. No need to create additional config files - everything reads from the frontend's `.env`
