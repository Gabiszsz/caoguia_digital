import re
import time
import json
import requests
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BACKEND_NOTICIAS_URL = "http://localhost:8080/api/noticias/sincronizar"
JWT_TOKEN = "eyJhbGciOiJIUzM4NCJ9.eyJzdWIiOiJhZG1pbkBjYW9ndWlhLmNvbSIsInBlcmZpbCI6IkFETUlOIiwiaWF0IjoxNzk0NTEyMTczLCJleHAiOjIxMDk4NzIxNzN9.sJGsH-vp61H9InDdpk4AhMsOqTgpHGt3l7ObkJYTSHdMVme0WsdkFbJtwdYgK4T4"


def iniciar_driver():
    options = webdriver.ChromeOptions()
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-notifications')
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    return webdriver.Chrome(options=options)


def limpar_texto(texto):
    if not texto:
        return ""
    texto = re.sub(r'[\U00010000-\U0010FFFF]', '', texto)
    texto = re.sub(r'[\u2600-\u27BF\uFE0F\u200D]', '', texto)
    texto = re.sub(r'\?{2,}', '', texto)
    return re.sub(r'[ \t]{2,}', ' ', texto).strip()


def extrair_data_post(driver):
    try:
        iso_str = driver.find_element(By.XPATH, "//time[@datetime]").get_attribute("datetime")
        if iso_str:
            dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
            return dt.astimezone().replace(tzinfo=None).isoformat(timespec="seconds")
    except Exception:
        pass
    return datetime.now().isoformat(timespec="seconds")


def gerar_titulo(legenda):
    frase = legenda.split("\n")[0].strip()
    if "." in frase and len(frase.split(".")[0]) >= 25:
        frase = frase.split(".")[0].strip()
    return frase if len(frase) <= 90 else frase[:87].rsplit(" ", 1)[0] + "..."


def extrair_ultimas_postagens(driver, quantidade=8):
    driver.get("https://www.instagram.com/caoguiaurutai/")
    time.sleep(5)

    for btn in driver.find_elements(
        By.XPATH,
        "//div[@role='dialog']//button | //svg[@aria-label='Fechar']/ancestor::button | //svg[@aria-label='Close']/ancestor::button"
    ):
        try:
            btn.click()
            time.sleep(1)
        except Exception:
            pass

    for scroll_y in (800, 1600):
        driver.execute_script(f"window.scrollTo(0, {scroll_y});")
        time.sleep(2)

    grid_items = WebDriverWait(driver, 15).until(
        EC.presence_of_all_elements_located((By.XPATH, "//a[contains(@href, '/p/') or contains(@href, '/reel/')]"))
    )

    candidatos, vistos = [], set()
    for item in grid_items:
        link = (item.get_attribute("href") or "").split("?")[0]
        if not link or link in vistos:
            continue
        vistos.add(link)
        img_url, alt = "", ""
        try:
            img = item.find_element(By.TAG_NAME, "img")
            img_url = img.get_attribute("src") or ""
            alt = img.get_attribute("alt") or ""
        except Exception:
            pass
        candidatos.append((link, img_url, alt))
        if len(candidatos) >= 10:
            break

    resultados = []
    for link, img_url, alt in candidatos:
        driver.get(link)
        time.sleep(3)

        data_iso = extrair_data_post(driver)
        legenda = ""
        for h1 in driver.find_elements(By.XPATH, "//h1"):
            txt = (h1.text or "").strip()
            if len(txt) > 15 and not txt.lower().startswith("photo by "):
                legenda = txt
                break

        if not legenda:
            try:
                meta = driver.find_element(By.XPATH, "//meta[@property='og:title']").get_attribute("content") or ""
                if ":" in meta:
                    legenda = meta.split(":", 1)[1].strip().strip('"“”')
            except Exception:
                pass

        if not legenda and alt and len(alt) > 20 and not alt.lower().startswith("photo by "):
            legenda = alt

        legenda = limpar_texto(legenda)
        if not legenda:
            continue

        titulo = gerar_titulo(legenda)
        resultados.append({
            "linkPostagem": link[:250],
            "urlImagem": img_url[:250],
            "textoDescricao": legenda,
            "noticiaUnificada": {
                "fonteOrigem": "INSTAGRAM",
                "linkOrigem": link,
                "titulo": titulo,
                "conteudo": legenda,
                "imagemUrl": img_url,
                "publicadoEm": data_iso,
                "audiodescricaoIA": None
            }
        })

    resultados.sort(key=lambda r: r["noticiaUnificada"]["publicadoEm"], reverse=True)
    return resultados[:quantidade]


def main():
    headers = {"Content-Type": "application/json; charset=utf-8", "Authorization": f"Bearer {JWT_TOKEN}"}
    driver = iniciar_driver()
    try:
        posts = extrair_ultimas_postagens(driver, quantidade=8)
    finally:
        driver.quit()

    for dados in posts:
        nu = dados["noticiaUnificada"]
        try:
            resp = requests.post(
                BACKEND_NOTICIAS_URL,
                data=json.dumps(nu, ensure_ascii=False).encode("utf-8"),
                headers=headers,
                timeout=180
            )
            print(f"[{resp.status_code}] {nu['publicadoEm']} - {nu['titulo']}")
        except Exception as e:
            print(f"[ERRO] Falha ao enviar '{nu['titulo']}': {e}")


if __name__ == "__main__":
    main()