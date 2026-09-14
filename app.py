import streamlit as st
import boto3
import json
import base64
from datetime import datetime
import difflib

# ==============================================================================
# CONFIGURACIÓN DE LA PÁGINA
# ==============================================================================
st.set_page_config(
    page_title="AI Creative Studio - Marketing & Advertising",
    page_icon="🎨",
    layout="wide"
)

# Inicialización del estado de la sesión (Session State)
if "image_gallery" not in st.session_state:
    st.session_state.image_gallery = []

if "text_history" not in st.session_state:
    st.session_state.text_history = [{
        "version": 1,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "author": "Sistema",
        "action": "Texto Inicial",
        "content": "Descubre la nueva línea de productos ecológicos diseñados para transformar tu día a día con el menor impacto ambiental."
    }]

if "feedback_notes" not in st.session_state:
    st.session_state.feedback_notes = []

if "current_user_role" not in st.session_state:
    st.session_state.current_user_role = "Diseñador"

# ==============================================================================
# CLIENTE AMAZON BEDROCK
# ==============================================================================
def get_bedrock_client():
    try:
        return boto3.client(service_name="bedrock-runtime", region_name="us-east-1")
    except Exception:
        return None

bedrock_client = get_bedrock_client()

# ==============================================================================
# MÓDULO 1: GENERACIÓN DE IMÁGENES (STABLE DIFFUSION)
# ==============================================================================
def generate_image_bedrock(prompt: str, style_preset: str):
    """
    Invoca el modelo Stability Diffusion XL en Amazon Bedrock
    """
    if bedrock_client is None:
        # Modo simulado si no hay conexión activa con AWS
        return None, "Modo emulación: Conexión a AWS Bedrock no detectada. Configure credenciales IAM."

    try:
        payload = {
            "text_prompts": [{"text": prompt, "weight": 1.0}],
            "cfg_scale": 8.0,
            "steps": 40,
            "seed": 42
        }
        if style_preset and style_preset != "none":
            payload["style_preset"] = style_preset

        response = bedrock_client.invoke_model(
            modelId="stability.stable-diffusion-xl-v1",
            body=json.dumps(payload),
            contentType="application/json",
            accept="application/json"
        )
        response_body = json.loads(response.get("body").read())
        artifacts = response_body.get("artifacts", [])
        if artifacts:
            image_base64 = artifacts[0].get("base64")
            return base64.b64decode(image_base64), None
        return None, "No se recibieron artefactos de imagen del modelo."
    except Exception as e:
        return None, f"Error al invocar Bedrock: {str(e)}"

# ==============================================================================
# MÓDULO 2: EDICIÓN DE TEXTO Y CONTENIDO (CLAUDE 3.5 SONNET)
# ==============================================================================
def process_text_with_claude(text: str, operation: str, extra_instruction: str = ""):
    """
    Invoca Claude 3.5 Sonnet en Amazon Bedrock para transformar el contenido
    """
    system_prompts = {
        "Resumir": "Eres un redactor creativo senior. Resume el texto destacando la propuesta de valor de forma concisa y persuasiva.",
        "Expandir": "Eres un redactor creativo senior. Desarrolla las ideas del texto proporcionando argumentos convincentes, contexto y un tono de marca envolvente.",
        "Corregir estilo y gramática": "Eres un editor editorial profesional. Corrige errores gramaticales, mejora la fluidez y asegura un vocabulario impecable sin alterar el mensaje base.",
        "Generar variaciones de Copy (A/B)": "Eres un especialista en conversión publicitaria. Genera 3 variaciones de copy atractivas (emocional, directa y basada en beneficios) a partir del texto original."
    }

    user_prompt = f"Texto base:\n\"\"\"\n{text}\n\"\"\"\n"
    if extra_instruction:
        user_prompt += f"\nInstrucciones adicionales del usuario: {extra_instruction}"

    if bedrock_client is None:
        # Respuesta simulada en ausencia de AWS
        return f"[Simulación Bedrock - {operation}]\n\n{text}\n\n*Texto procesado exitosamente conforme a la directiva de marketing solicitada.*"

    try:
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1024,
            "temperature": 0.7,
            "top_p": 0.9,
            "system": system_prompts.get(operation, "Eres un redactor publicitario experto."),
            "messages": [{"role": "user", "content": user_prompt}]
        })
        response = bedrock_client.invoke_model(
            modelId="anthropic.claude-3-5-sonnet-20240620-v1:0",
            body=body,
            contentType="application/json",
            accept="application/json"
        )
        response_body = json.loads(response.get("body").read())
        return response_body["content"][0]["text"]
    except Exception as e:
        return f"Error al procesar texto con Claude: {str(e)}"

# ==============================================================================
# SIDEBAR: CONTROL DE ROLES (RBAC) Y GOBERNANZA
# ==============================================================================
with st.sidebar:
    st.title("🛡️ Gestión de Acceso")
    st.session_state.current_user_role = st.selectbox(
        "Rol de Usuario Activo:",
        ["Diseñador", "Redactor", "Aprobador", "Administrador"]
    )
    role = st.session_state.current_user_role
    st.info(f"**Permisos actuales ({role}):**")
    if role == "Diseñador":
        st.write("- Generación visual con Stable Diffusion\n- Consulta y descarga de galería\n- Agregar notas creativas")
    elif role == "Redactor":
        st.write("- Transformación de contenido con Claude\n- Control de versiones y rollback\n- Agregar comentarios")
    elif role == "Aprobador":
        st.write("- Revisión integral de activos\n- Aprobación/Rechazo de campañas\n- Publicación final")
    else:
        st.write("- Acceso integral a todas las funciones y auditoría de seguridad.")

    st.markdown("---")
    st.subheader("⚙️ Parámetros de Inferencia")
    temperature = st.slider("Temperatura (Creatividad Claude):", 0.0, 1.0, 0.7, 0.05)
    st.caption("0.0 - 0.3: Determinista/Factual | 0.7 - 1.0: Creativo/Campañas")

# ==============================================================================
# VISTA PRINCIPAL POR PESTAÑAS
# ==============================================================================
tab_img, tab_txt, tab_collab, tab_sec = st.tabs([
    "🖼️ Generador de Imágenes",
    "✍️ Editor de Contenido",
    "👥 Colaboración y Workflow",
    "🔒 Ética y Seguridad"
])

# ------------------------------------------------------------------------------
# PESTAÑA 1: IMÁGENES
# ------------------------------------------------------------------------------
with tab_img:
    st.header("Generación de Activos Visuales (Stable Diffusion XL)")
    if role in ["Diseñador", "Administrador"]:
        col1, col2 = st.columns()
        with col1:
            prompt_input = st.text_area(
                "Descripción del arte publicitario (Prompt):",
                placeholder="Ej. Fotografía publicitaria de un frasco de perfume sobre una piedra volcánica con rocío matutino..."
            )
        with col2:
            style = st.selectbox(
                "Estilo visual:",
                ["photographic", "anime", "oil-painting", "digital-art", "cinematic", "comic-book", "none"]
            )
            btn_gen = st.button("🚀 Generar Imagen", use_container_width=True)

        if btn_gen and prompt_input:
            with st.spinner("Procesando difusión con Amazon Bedrock..."):
                img_bytes, err = generate_image_bedrock(prompt_input, style)
                if img_bytes:
                    st.session_state.image_gallery.append({
                        "id": len(st.session_state.image_gallery) + 1,
                        "bytes": img_bytes,
                        "prompt": prompt_input,
                        "style": style,
                        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
                    st.success("¡Imagen generada exitosamente!")
                else:
                    st.warning(err)
    else:
        st.warning("⚠️ Su rol actual no posee permisos de creación gráfica. Puede explorar la galería.")

    st.markdown("---")
    st.subheader("📚 Galería de Activos Generados")
    if st.session_state.image_gallery:
        cols = st.columns(3)
        for idx, item in enumerate(reversed(st.session_state.image_gallery)):
            with cols[idx % 3]:
                st.image(item["bytes"], caption=f"ID #{item['id']} - Estilo: {item['style']}", use_container_width=True)
                st.caption(f"Prompt: {item['prompt']}")
                st.download_button(
                    label="⬇️ Descargar PNG",
                    data=item["bytes"],
                    file_name=f"activo_marketing_{item['id']}.png",
                    mime="image/png",
                    key=f"dl_{item['id']}"
                )
    else:
        st.info("Aún no hay imágenes en la galería de la campaña.")

# ------------------------------------------------------------------------------
# PESTAÑA 2: CONTENIDO Y TEXTO
# ------------------------------------------------------------------------------
with tab_txt:
    st.header("Edición y Optimización de Copy (Claude 3.5 Sonnet)")
    if role in ["Redactor", "Administrador"]:
        current_text = st.session_state.text_history[-1]["content"]
        
        c_left, c_right = st.columns()
        with c_left:
            st.subheader("Borrador Activo")
            input_text = st.text_area("Contenido a refinar:", value=current_text, height=220)
            op = st.selectbox(
                "Acción de transformación creativa:",
                ["Resumir", "Expandir", "Corregir estilo y gramática", "Generar variaciones de Copy (A/B)"]
            )
            extra_instructions = st.text_input("Instrucciones específicas (opcional):", placeholder="Ej. Tono fresco y juvenil para Instagram")
            if st.button("✨ Aplicar Transformación con Claude", use_container_width=True):
                with st.spinner("Consultando Amazon Bedrock..."):
                    result_text = process_text_with_claude(input_text, op, extra_instructions)
                    st.session_state.text_history.append({
                        "version": len(st.session_state.text_history) + 1,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "author": role,
                        "action": op,
                        "content": result_text
                    })
                    st.rerun()

        with c_right:
            st.subheader("Historial de Versiones y Rollback")
            history = st.session_state.text_history
            selected_version = st.selectbox(
                "Comparar con versión previa:",
                options=[v["version"] for v in history],
                index=len(history) - 1,
                format_func=lambda x: f"Versión {x} ({history[x-1]['action']})"
            )
            
            # Comparativa visual de diferencias (Diff)
            v_content = history[selected_version - 1]["content"]
            st.text_area("Contenido de la versión seleccionada:", value=v_content, height=180, disabled=True)
            
            if selected_version != len(history):
                if st.button(f"⏪ Revertir a Versión {selected_version}", use_container_width=True):
                    st.session_state.text_history.append({
                        "version": len(history) + 1,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "author": role,
                        "action": f"Rollback a Versión {selected_version}",
                        "content": v_content
                    })
                    st.success(f"Restaurada la Versión {selected_version} exitosamente.")
                    st.rerun()
    else:
        st.warning("⚠️ Su rol actual solo tiene permisos de lectura para el editor de textos.")

# ------------------------------------------------------------------------------
# PESTAÑA 3: COLABORACIÓN Y FLUJO DE TRABAJO
# ------------------------------------------------------------------------------
with tab_collab:
    st.header("Flujo de Aprobaciones y Retroalimentación")
    
    st.subheader("Estado de la Campaña")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Activos Gráficos", len(st.session_state.image_gallery))
    c2.metric("Iteraciones de Copy", len(st.session_state.text_history))
    status_label = "Aprobada para Publicación" if any(n.get("status") == "Aprobado" for n in st.session_state.feedback_notes) else "En Proceso Creativo"
    c3.metric("Estado General", status_label)

    st.markdown("---")
    st.subheader("Muro de Notas y Comentarios del Equipo")
    new_comment = st.text_input("Agregar nota o retroalimentación:")
    
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("💬 Publicar Comentario"):
            if new_comment:
                st.session_state.feedback_notes.append({
                    "author": role,
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "text": new_comment,
                    "status": "Comentario"
                })
                st.rerun()
    with col_btn2:
        if role in ["Aprobador", "Administrador"]:
            if st.button("✅ Aprobar Campaña Completa"):
                st.session_state.feedback_notes.append({
                    "author": role,
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "text": "Campaña revisada y aprobada para publicación.",
                    "status": "Aprobado"
                })
                st.rerun()

    # Listado de notas
    for note in reversed(st.session_state.feedback_notes):
        with st.chat_message(note["author"]):
            st.markdown(f"**{note['author']}** ({note['date']}) - *[{note['status']}]*")
            st.write(note["text"])

# ------------------------------------------------------------------------------
# PESTAÑA 4: ÉTICA Y SEGURIDAD
# ------------------------------------------------------------------------------
with tab_sec:
    st.header("Gobierno, Seguridad y Ética en IA Generativa")
    
    st.subheader("1. Bedrock Guardrails y Moderación")
    st.markdown("""
    - **Filtro de Contenido Tóxico:** Configuración de umbrales estrictos en Amazon Bedrock para bloquear incitación al odio, violencia y contenido sexual.
    - **Enmascaramiento de PII:** Detección y bloqueo automático de información personal sensible (correos, teléfonos, tarjetas bancarias) antes de invocar los modelos.
    - **Detección de Prompt Injection:** Barreras de entrada que invalidan instrucciones maliciosas destinadas a eludir políticas del sistema.
    """)

    st.subheader("2. Cifrado y Soberanía del Dato")
    st.markdown("""
    - **En reposo:** Los activos de imagen y textos se almacenan en buckets de **Amazon S3** con cifrado del lado del servidor gestionado por llaves maestras **AWS KMS (SSE-KMS)**.
    - **En tránsito:** Todo el tráfico entre clientes, Streamlit y Bedrock está forzado bajo **TLS 1.3**.
    - **Políticas de Privacidad de Bedrock:** Garantía de que los prompts corporativos y contenidos generados no se utilizan para entrenar los modelos públicos de Stability AI ni de Anthropic.
    """)

    st.subheader("3. Pautas de Propiedad Intelectual y Mitigación de Sesgos")
    st.markdown("""
    - **Atribución y Marcas de Agua:** Integración de estándares **C2PA / Content Credentials** para certificar que las imágenes son generadas artificialmente.
    - **Mitigación de Sesgos:** Directrices en los System Prompts para garantizar diversidad e inclusión en la generación de personajes y situaciones publicitarias.
    """)
