from fastapi.testclient import TestClient

from api import main
from api.preprocess import infer_java_home_from_executable


class StubPredictor:
    device = "cpu"
    model_path = "stub"

    def predict(self, title: str, lead_paragraph: str) -> float:
        assert title == "Chinh phu uu tien dau tu 70 cong nghe cao"
        assert lead_paragraph == "Chinh phu ban hanh danh muc 70 cong nghe cao"
        return 0.8732


def test_predict_returns_clickbait_probability(monkeypatch):
    monkeypatch.setattr(main, "get_predictor", lambda: StubPredictor())
    client = TestClient(main.app)

    response = client.post(
        "/predict",
        json={
            "title": "  Chinh phu uu tien dau tu 70 cong nghe cao  ",
            "lead_paragraph": " Chinh phu ban hanh danh muc 70 cong nghe cao ",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"prob_clickbait": 0.8732}


def test_predict_rejects_empty_title(monkeypatch):
    monkeypatch.setattr(main, "get_predictor", lambda: StubPredictor())
    client = TestClient(main.app)

    response = client.post("/predict", json={"title": "   ", "lead_paragraph": ""})

    assert response.status_code == 422


def test_health_reports_ready_when_predictor_loads(monkeypatch):
    monkeypatch.setattr(main, "get_predictor", lambda: StubPredictor())
    client = TestClient(main.app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert response.json()["device"] == "cpu"


def test_private_network_preflight_is_allowed(monkeypatch):
    monkeypatch.setattr(main, "get_predictor", lambda: StubPredictor())
    client = TestClient(main.app)

    response = client.options(
        "/predict",
        headers={
            "Origin": "https://vnexpress.net",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
            "Access-Control-Request-Private-Network": "true",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-private-network"] == "true"


def test_infer_java_home_from_bin_executable():
    assert str(infer_java_home_from_executable(r"C:\Program Files\Java\jdk1.8.0_481\bin\java.exe")).endswith(
        r"Java\jdk1.8.0_481"
    )
