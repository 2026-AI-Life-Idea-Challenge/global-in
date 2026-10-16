from fastapi import FastAPI

app = FastAPI(
    title="Global-In API",
    version="0.1.0",
)


@app.get("/")
def root():
    return {"message": "Global-In API is running"}


@app.get("/health")
def health():
    return {"status": "ok"}