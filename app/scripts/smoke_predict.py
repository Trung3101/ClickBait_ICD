import time

import requests


CASES = [
    {
        "title": "Chinh phu uu tien dau tu 70 cong nghe cao",
        "lead_paragraph": (
            "Chinh phu ban hanh danh muc 70 cong nghe cao duoc uu tien dau tu phat trien, "
            "tap trung vao tri tue nhan tao, du lieu lon, dien toan dam may."
        ),
    },
    {
        "title": "Giong loc cuon sap mai ton, hang rao o TP HCM",
        "lead_paragraph": (
            "Con giong loc manh chieu 17/5 gay do hang rao, lam bay mai ton cua hang "
            "o khu vuc Tan Son Nhat, giao thong un u nghiem trong."
        ),
    },
]


def main():
    for case in CASES:
        started = time.perf_counter()
        response = requests.post("http://127.0.0.1:8000/predict", json=case, timeout=60)
        elapsed_ms = (time.perf_counter() - started) * 1000
        response.raise_for_status()
        print(
            f"{case['title']}: prob_clickbait={response.json()['prob_clickbait']:.4f}, "
            f"latency_ms={elapsed_ms:.1f}"
        )


if __name__ == "__main__":
    main()
