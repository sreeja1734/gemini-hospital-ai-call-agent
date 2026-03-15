"""
Locust load testing configuration for the Hospital AI Call Agent.

Run with: locust -f tests/locustfile.py --host=http://localhost:8000
"""
from locust import HttpUser, task, between, tag


class HospitalAIUser(HttpUser):
    """Simulates a hospital admin user accessing the dashboard."""
    wait_time = between(1, 3)
    token = None

    def on_start(self):
        """Login and store the JWT token."""
        response = self.client.post("/auth/login", json={
            "username": "admin",
            "password": "admin123",
        })
        if response.status_code == 200:
            self.token = response.json()["access_token"]

    @property
    def auth_headers(self):
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    @task(3)
    @tag("dashboard")
    def get_dashboard(self):
        """Load the dashboard data — most frequent admin action."""
        self.client.get("/get-dashboard-data", headers=self.auth_headers)

    @task(2)
    @tag("appointments")
    def list_appointments(self):
        self.client.get("/appointments/", headers=self.auth_headers)

    @task(1)
    @tag("transcripts")
    def list_transcripts(self):
        self.client.get("/transcripts", headers=self.auth_headers)

    @task(1)
    @tag("emergency")
    def get_emergency_alerts(self):
        self.client.get("/emergency-alerts", headers=self.auth_headers)

    @task(1)
    @tag("health")
    def health_check(self):
        self.client.get("/health")


class CallerUser(HttpUser):
    """Simulates a patient calling in."""
    wait_time = between(2, 5)

    @task
    @tag("call_flow")
    def full_call_flow(self):
        """Simulate a complete call: start → talk → end."""
        # Start conversation
        start_res = self.client.post("/start-conversation", json={
            "caller_phone": "+1234567890",
            "language": "en-US",
        })

        if start_res.status_code == 200:
            call_id = start_res.json().get("call_id")

            # Send a message
            self.client.post("/process-user-speech", json={
                "call_id": call_id,
                "text_input": "I would like to book an appointment with a cardiologist tomorrow.",
                "language": "en-US",
            })

            # End the call
            self.client.post("/end-call", json={
                "call_id": call_id,
            })
