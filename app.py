import streamlit as st
import pandas as pd
import requests

st.set_page_config(
    page_title="Secretaria Municipal de Educação - Agendamento",
    page_icon="📅",
    layout="wide"
)

WEB_APP_URL = "https://script.google.com/macros/s/AKfycbzmJ8a8CkB_TNWO4cOYM1clmGiN-hKv5E4NNc4x5uS2tR0P_qr_p8rc6n-G8doX11hq/exec"

st.title("SECRETARIA MUNICIPAL DE EDUCAÇÃO")
st.subheader("Sistema de Agendamento da Sala de Reuniões")
st.markdown("---")

COLUNAS_ESPERADAS = [
    "Responsavel", "Data", "Hora_Inicio", "Hora_Termino", 
    "Sala", "Data_Show", "Motivo", "Observacoes"
]

def carregar_dados():
    try:
        response = requests.get(WEB_APP_URL)
        data_json = response.json()
        
        if isinstance(data_json, list) and len(data_json) > 0:
            header = data_json[0]
            rows = data_json[1:]
            if len(rows) > 0:
                df = pd.DataFrame(rows, columns=header)
                # Normaliza o nome da coluna de término caso esteja como 'Hora_Ternibi'
                if "Hora_Ternibi" in df.columns and "Hora_Termino" not in df.columns:
                    df.rename(columns={"Hora_Ternibi": "Hora_Termino"}, inplace=True)
                
                for col in COLUNAS_ESPERADAS:
                    if col not in df.columns:
                        df[col] = ""
                return df
        
        return pd.DataFrame(columns=COLUNAS_ESPERADAS)
    except Exception:
        return pd.DataFrame(columns=COLUNAS_ESPERADAS)

def limpar_str(val):
    s = str(val).strip().replace("'", "")
    if "T" in s:
        s = s.split("T")[1]
    if "." in s:
        s = s.split(".")[0]
    partes = s.split(":")
    if len(partes) >= 2:
        return f"{partes[0].zfill(2)}:{partes[1].zfill(2)}"
    return s

def limpar_data(val):
    s = str(val).strip()
    if "T" in s:
        return s.split("T")[0]
    return s[:10]

df_agendamentos = carregar_dados()

col1, col2 = st.columns([2, 1])

with col1:
    st.header("Novo Agendamento")
    st.caption("Preencha os dados para reservar a sala de reuniões.")

    with st.form("form_agendamento", clear_on_submit=True):
        responsavel = st.text_input("Nome do responsável:")
        
        c_data, c_inicio, c_fim = st.columns(3)
        with c_data:
            data_reuniao = st.date_input("Data da reunião:")
        with c_inicio:
            hora_inicio = st.time_input("Horário de início:")
        with c_fim:
            hora_termino = st.time_input("Horário de término:")

        sala = "Sala de Reuniões da Secretaria"

        motivo = st.text_area("Motivo da reunião:")
        data_show = st.radio("Vai precisar de data show?", ["Sim", "Não"], horizontal=True)
        observacoes = st.text_area("Observações adicionais:")

        btn_confirmar = st.form_submit_button("CONFIRMAR AGENDAMENTO")

    if btn_confirmar:
        if not responsavel.strip():
            st.error("⚠️ Por favor, informe o nome do responsável!")
        elif hora_inicio >= hora_termino:
            st.error("⚠️ O horário de término deve ser posterior ao horário de início!")
        else:
            df_atual = carregar_dados()
            data_str = str(data_reuniao)
            
            t_novo_ini_str = hora_inicio.strftime("%H:%M")
            t_novo_fim_str = hora_termino.strftime("%H:%M")
            
            # Converte o novo agendamento para minutos totais do dia
            ni_min = int(t_novo_ini_str.split(":")[0]) * 60 + int(t_novo_ini_str.split(":")[1])
            nf_min = int(t_novo_fim_str.split(":")[0]) * 60 + int(t_novo_fim_str.split(":")[1])
            
            tem_conflito = False

            if not df_atual.empty:
                for _, row in df_atual.iterrows():
                    resp_existente = str(row.get("Responsavel", "")).strip().replace("'", "")
                    if not resp_existente or resp_existente.lower() == "nan":
                        continue
                    
                    # Pega a data da linha (procurando em chaves possíveis)
                    val_data = row.get("Data", "")
                    data_existente = limpar_data(val_data)
                    
                    if data_existente == data_str:
                        # Pega início e término lidando com variações de nome de coluna
                        val_ini = row.get("Hora_Inicio", "")
                        val_fim = row.get("Hora_Termino", "") or row.get("Hora_Ternibi", "")
                        
                        h_ini_existente = limpar_str(val_ini)
                        h_fim_existente = limpar_str(val_fim)
                        
                        if not h_ini_existente or not h_fim_existente or len(h_ini_existente) < 5:
                            continue
                            
                        try:
                            ei_min = int(h_ini_existente.split(":")[0]) * 60 + int(h_ini_existente.split(":")[1])
                            ef_min = int(h_fim_existente.split(":")[0]) * 60 + int(h_fim_existente.split(":")[1])
                            
                            # VALIDAÇÃO DE SOBREPOSIÇÃO BLINDADA:
                            # Qualquer cruzamento de intervalos resulta em conflito
                            if max(ni_min, ei_min) < min(nf_min, ef_min):
                                tem_conflito = True
                                break
                        except Exception:
                            pass

            if tem_conflito:
                st.error("❌ Sala de reunião já agendada neste horário e data!")
            else:
                novo_dado = {
                    "Responsavel": responsavel,
                    "Data": data_str,
                    "Hora_Inicio": t_novo_ini_str,
                    "Hora_Termino": t_novo_fim_str,
                    "Sala": sala,
                    "Data_Show": data_show,
                    "Motivo": motivo,
                    "Observacoes": observacoes
                }
                
                try:
                    requests.post(WEB_APP_URL, json=novo_dado)
                    st.success("✅ Agendamento realizado com sucesso!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao enviar dados: {e}")

with col2:
    st.header("PRÓXIMAS REUNIÕES")
    if not df_agendamentos.empty and "Responsavel" in df_agendamentos.columns:
        df_validos = df_agendamentos[df_agendamentos["Responsavel"].astype(str).str.strip().str.replace("'", "") != ""]
        if not df_validos.empty:
            for _, row in df_validos.iterrows():
                d_limpa = limpar_data(row['Data'])
                val_fim_col = row.get('Hora_Termino', '') or row.get('Hora_Ternibi', '')
                h_ini_limpa = limpar_str(row['Hora_Inicio'])
                h_fim_limpa = limpar_str(val_fim_col)
                
                with st.container(border=True):
                    st.markdown(f"**{d_limpa} | {h_ini_limpa} - {h_fim_limpa}**")
                    st.markdown(f"👤 Responsável: {str(row['Responsavel']).replace("'", "")}")
                    motivo_val = str(row.get('Motivo', '')).replace("'", "")
                    if motivo_val and motivo_val.lower() != "nan":
                        st.caption(f"Motivo: {motivo_val}")
        else:
            st.info("Nenhuma reunião agendada ainda.")
    else:
        st.info("Nenhuma reunião agendada ainda.")