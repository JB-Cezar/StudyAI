#!/usr/bin/env python3
"""
Script opcional: conecta o Google Calendar uma vez pelo terminal.

Útil se o botão "Conectar" no Streamlit não abrir o navegador.
Gera/atualiza token.json na pasta do projeto.

Uso:
  source .venv/bin/activate
  python setup_calendar_auth.py
"""
 
import calendar_service as cal


def main() -> None:
    print("StudyAI — autenticação Google Calendar")
    if not cal.credentials_configured():
        print("\nErro: credentials.json não encontrado.")
        print("Leia SETUP_CALENDAR.md e baixe as credenciais OAuth (Desktop).")
        return

    # interactive=True abre o navegador para OAuth
    eventos = cal.list_upcoming_events(interactive=True)
    print(f"\nConectado. {len(eventos)} evento(s) nos próximos 14 dias.\n")
    for evento in eventos[:10]:
        print(cal.format_event_line(evento))
    if len(eventos) > 10:
        print(f"... e mais {len(eventos) - 10} evento(s).")
    print("\nAgora rode: streamlit run app2.py")


if __name__ == "__main__":
    main()
