# Panel (Dashboard Campañas)

Repositorio con la app Streamlit para el Dashboard de Campañas.

Archivos importantes:
- app.py : aplicación principal de Streamlit.
- requirements.txt : dependencias.

Despliegue en Streamlit Community:
1. Hacer push a GitHub.
2. Entrar a https://share.streamlit.io y conectar la cuenta de GitHub.
3. Crear una nueva app seleccionando el repo `MichCastilloA/Panel`, la rama (por ejemplo `main`) y el archivo `app.py`.
4. Deploy. Streamlit instalará las dependencias y servirá la app.

Notas:
- Si tu app lee archivos en rutas de red (p. ej. `\\fc-fs01\...`), esos recursos NO serán accesibles desde Streamlit Cloud. Mueve los datos a un storage accesible (S3, Google Cloud Storage) o adapta la app para subir CSV por la UI, o mantén la app corriendo localmente y usa ngrok para acceso temporal.
- Para cambios: push -> Streamlit auto-reconstruye la app.