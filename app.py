import calendar
import html
import unicodedata
from pathlib import Path
from datetime import date, datetime, time, timedelta

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="SEMED | Agendamento de Reuniões", page_icon="📅", layout="wide", initial_sidebar_state="expanded")
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbzmJ8a8CkB_TNWO4cOYM1clmGiN-hKv5E4NNc4x5uS2tR0P_qr_p8rc6n-G8doX11hq/exec"
COLUNAS = ["Responsavel", "Data", "Hora_Inicio", "Hora_Termino", "Sala", "Data_Show", "Motivo", "Observacoes"]
MESES = ["", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html,body,[class*="css"], [data-testid="stApp"] {font-family:'Inter',sans-serif}
.stApp {background:#f5f8f5;color:#173a2a}
[data-testid="stSidebar"] {background:#21A351 !important;}
[data-testid="stSidebar"] * {color:white !important}
[data-testid="stSidebar"] [data-testid="stImage"] {background:transparent !important; padding:0 !important; border:0 !important; border-radius:0 !important; box-shadow:none !important; margin-bottom:12px}
[data-testid="stSidebar"] [data-testid="stImage"] img {width:100%; height:auto; object-fit:contain; background:transparent !important; border-radius:0 !important}
[data-testid="stSidebar"] [data-testid="stRadio"] label {padding:7px 0}
.block-container {padding-top:1.5rem;max-width:1650px}
h1,h2,h3 {color:#10462d !important;letter-spacing:-.025em}
[data-testid="stVerticalBlockBorderWrapper"] {background:#fff;border:1px solid #e0e9e1 !important;border-radius:16px !important;box-shadow:0 4px 16px #174a2810}
.stButton button[kind="primary"], [data-testid="stFormSubmitButton"] button {background:#008a4b;color:white;border:0;border-radius:9px;font-weight:700;min-height:45px}
.stButton button[kind="primary"]:hover,[data-testid="stFormSubmitButton"] button:hover {background:#006e3d;color:white}
.stButton button {border-radius:9px}
input,textarea {border-radius:9px !important}
.hero {padding:26px 30px;border-radius:17px;background:linear-gradient(100deg,#ffffff 15%,#e5f7df 100%);border:1px solid #dfecdf;margin-bottom:18px;position:relative;overflow:hidden}
.hero:after {content:'';position:absolute;right:-35px;top:-80px;width:240px;height:240px;border:42px solid #ffdc26;border-radius:50%;opacity:.5}
.hero h1 {font-size:2rem;margin:0;line-height:1.18;position:relative;z-index:1}
.hero p {margin:10px 0 0;color:#4c715e;position:relative;z-index:1}
.eyebrow {color:#008a4b;font-size:.76rem;font-weight:800;letter-spacing:.13em;text-transform:uppercase}
.metric {background:#fff;border:1px solid #e1ebe2;border-radius:13px;padding:17px 18px;min-height:110px}
.metric .number {font-size:1.85rem;font-weight:800;color:#11663c;margin-top:6px}
.metric .label {font-size:.79rem;color:#5c7364;font-weight:600}
.section-title {font-weight:800;color:#13482e;font-size:1.22rem;margin-bottom:4px}
.muted {color:#748477;font-size:.83rem}
.booking {border:1px solid #e2eae1;border-left:4px solid #00b85c;background:#fff;padding:13px 14px;border-radius:10px;margin:9px 0}
.booking strong {color:#144b30;font-size:.92rem}
.booking small {color:#617768}
.calendar {width:100%;border-collapse:separate;border-spacing:4px;table-layout:fixed}
.calendar th {font-size:.71rem;color:#698070;text-align:center;padding:9px 0}
.calendar td {text-align:center;border-radius:9px;background:#f4f8f4;height:48px;color:#27563a;font-weight:600;font-size:.9rem}
.calendar td.other {background:transparent;color:#b9c6bb}
.calendar td.today {outline:2px solid #008a4b}
.calendar td.booked {background:#d6f4dc;color:#006b38}
.calendar td.past {color:#a6b6a8}
.dot {display:inline-block;width:7px;height:7px;background:#fa6833;border-radius:50%;margin-left:4px;vertical-align:middle}
.note {padding:11px 13px;background:#fff7db;border-left:3px solid #f9b42b;border-radius:8px;color:#775b17;font-size:.83rem}
.footer {margin:30px 0 8px;color:#6e8374;font-size:.78rem;text-align:center}
</style>""", unsafe_allow_html=True)


def safe(value):
    return html.escape(str(value))


def normalizar_data(value):
    if value is None or str(value).lower() in ("nan", "nat", ""):
        return ""
    s = str(value).strip().replace("'", "")
    try:
        return pd.to_datetime(s, dayfirst=('/' in s), errors='raise').strftime('%Y-%m-%d')
    except (ValueError, TypeError):
        return s.split('T')[0][:10]


def normalizar_hora(value):
    s = str(value).strip().replace("'", "")
    if not s or s.lower() == "nan":
        return ""
    if 'T' in s:
        s = s.split('T')[-1]
    parts = s.split(':')
    if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
        return f"{int(parts[0]):02d}:{int(parts[1]):02d}"
    return ""


def minutos(value):
    h = normalizar_hora(value)
    if not h:
        return None
    a, b = map(int, h.split(':'))
    return a * 60 + b if a < 24 and b < 60 else None


def normalizar_campo(nome):
    """Aceita cabeçalhos com espaços, acentos e pequenas variações."""
    texto = unicodedata.normalize('NFKD', str(nome).strip())
    texto = ''.join(c for c in texto if not unicodedata.combining(c))
    return ''.join(c for c in texto.lower() if c.isalnum())


def pediu_data_show(valor):
    """Interpreta valores comuns retornados pelo Google Sheets/Apps Script."""
    if isinstance(valor, bool):
        return valor
    if pd.isna(valor):
        return False
    texto = unicodedata.normalize('NFKD', str(valor).strip().lower())
    texto = ''.join(c for c in texto if not unicodedata.combining(c))
    texto = ' '.join(texto.replace("'", '').split())
    return texto in ('sim', 's', 'yes', 'true', 'verdadeiro', '1', 'com data show', 'com datashow', 'solicitado', 'necessita', 'precisa')


def carregar_dados():
    response = requests.get(WEB_APP_URL, timeout=18)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, list):
        raise ValueError('Formato de dados inesperado no Google Apps Script.')
    if not data:
        return pd.DataFrame(columns=COLUNAS)
    header, *rows = data
    df = pd.DataFrame(rows, columns=header)
    aliases = {'datashow': 'Data_Show', 'precisadedatashow': 'Data_Show',
               'solicitoudatashow': 'Data_Show', 'usardatashow': 'Data_Show',
               'horaternibi': 'Hora_Termino', 'horatermino': 'Hora_Termino'}
    df.rename(columns={c: aliases[normalizar_campo(c)] for c in df.columns
                       if normalizar_campo(c) in aliases}, inplace=True)
    if 'Hora_Ternibi' in df.columns and 'Hora_Termino' not in df.columns:
        df.rename(columns={'Hora_Ternibi':'Hora_Termino'}, inplace=True)
    for col in COLUNAS:
        if col not in df.columns:
            df[col] = ''
    df = df[df['Responsavel'].astype(str).str.strip().str.replace("'", "", regex=False).ne('')].copy()
    df['Data_Show_Solicitado'] = df['Data_Show'].map(pediu_data_show)
    df['Data_Normalizada'] = df['Data'].map(normalizar_data)
    df['Inicio_Normalizado'] = df['Hora_Inicio'].map(normalizar_hora)
    df['Fim_Normalizado'] = df['Hora_Termino'].map(normalizar_hora)
    return df


def tem_conflito(df, dia, inicio, fim):
    for _, r in df[df['Data_Normalizada'] == dia].iterrows():
        a, b = minutos(r['Inicio_Normalizado']), minutos(r['Fim_Normalizado'])
        if a is not None and b is not None and max(inicio, a) < min(fim, b):
            return True
    return False


def render_reserva(row):
    d = row['Data_Normalizada']
    try:
        d = datetime.strptime(d, '%Y-%m-%d').strftime('%d/%m/%Y')
    except ValueError:
        pass
    motivo = str(row.get('Motivo', '')).replace("'", '').strip()
    if not motivo or motivo.lower() == 'nan':
        motivo = 'Reunião agendada'
    ds = 'Com data show' if pediu_data_show(row.get('Data_Show', '')) else 'Sem data show'
    st.markdown(f'''<div class="booking"><strong>{safe(motivo)}</strong><br>
    <small>📅 {safe(d)} &nbsp; ⏰ {safe(row['Inicio_Normalizado'])} – {safe(row['Fim_Normalizado'])}<br>
    👤 {safe(str(row['Responsavel']).replace("'", ""))} &nbsp; · &nbsp; {safe(ds)}</small></div>''', unsafe_allow_html=True)


def calendario_html(ano, mes, datas_reservadas):
    hoje = date.today()
    semanas = calendar.Calendar(firstweekday=6).monthdatescalendar(ano, mes)
    result = '<table class="calendar"><thead><tr>' + ''.join(f'<th>{dia}</th>' for dia in ['DOM','SEG','TER','QUA','QUI','SEX','SÁB']) + '</tr></thead><tbody>'
    for semana in semanas:
        result += '<tr>'
        for dia in semana:
            classes = []
            if dia.month != mes: classes.append('other')
            if dia == hoje: classes.append('today')
            if dia < hoje: classes.append('past')
            if dia.isoformat() in datas_reservadas and dia.month == mes: classes.append('booked')
            dot = '<span class="dot"></span>' if dia.isoformat() in datas_reservadas and dia.month == mes else ''
            result += f'<td class="{" ".join(classes)}">{dia.day}{dot}</td>'
        result += '</tr>'
    return result + '</tbody></table>'


with st.sidebar:
    logo_path = Path(__file__).resolve().parent / 'logo_semed_nova.jpeg'
    if logo_path.exists():
        st.image(str(logo_path), use_container_width=True)
    else:
        st.markdown('## SEMED')
        st.caption('SECRETARIA MUNICIPAL DE EDUCAÇÃO')
    st.divider()
    pagina = st.radio('Navegação', ['🏠 Início', '➕ Novo Agendamento', '📅 Calendário', '📋 Todas as Reservas', '📊 Relatórios'], label_visibility='collapsed')
    st.divider()
    st.markdown('**Núcleo de Tecnologias Educacionais**')
    st.caption('Sistema de agendamento da sala de reuniões')

st.markdown('''<div class="hero"><div class="eyebrow">Secretaria Municipal de Educação</div>
<h1>Sistema de Agendamento<br>da Sala de Reuniões</h1>
<p>Organize suas reuniões, consulte a disponibilidade e solicite o data show em um só lugar.</p></div>''', unsafe_allow_html=True)

try:
    df = carregar_dados()
    carregou = True
except (requests.RequestException, ValueError, KeyError) as exc:
    df = pd.DataFrame(columns=COLUNAS + ['Data_Normalizada','Inicio_Normalizado','Fim_Normalizado','Data_Show_Solicitado'])
    carregou = False
    st.error(f'Não foi possível consultar os agendamentos. Confira a conexão com o Google Apps Script. Detalhes: {exc}')

hoje = date.today().isoformat()
validos = df[df['Data_Normalizada'].ge(hoje)].sort_values(['Data_Normalizada','Inicio_Normalizado']) if not df.empty else df
reunioes_hoje = df[df['Data_Normalizada'] == hoje] if not df.empty else df

if pagina == '🏠 Início':
    a,b,c,d = st.columns(4)
    for col, label, numero in [(a,'Reservas futuras',len(validos)),(b,'Reuniões hoje',len(reunioes_hoje)),(c,'Dias com reservas',validos['Data_Normalizada'].nunique()),(d,'Com data show',int(validos['Data_Show_Solicitado'].sum()))]:
        with col:
            st.markdown(f'<div class="metric"><div class="label">{label}</div><div class="number">{numero}</div></div>', unsafe_allow_html=True)
    # Diagnóstico sem alterar os dados armazenados.
    if not validos.empty and not validos['Data_Show_Solicitado'].any():
        with st.expander('Conferir informações de data show'):
            st.caption('Valores recebidos da coluna Data_Show do Google Apps Script:')
            st.write(validos['Data_Show'].astype(str).value_counts(dropna=False).to_frame('Quantidade'))
            st.caption('Se todos estiverem vazios ou incorretos, será necessário conferir o retorno do Apps Script e a coluna da planilha.')
    st.write('')

if pagina in ('🏠 Início', '➕ Novo Agendamento'):
    col_form, col_right = st.columns([1.3,1], gap='medium')
    with col_form:
        with st.container(border=True):
            st.markdown('<div class="section-title">➕ Novo Agendamento</div><div class="muted">Preencha os dados para reservar a sala de reuniões.</div>', unsafe_allow_html=True)
            with st.form('form_agendamento', clear_on_submit=False):
                responsavel = st.text_input('Nome do responsável *', placeholder='Digite o nome completo')
                c1,c2,c3 = st.columns(3)
                with c1: data_reuniao = st.date_input('Data da reunião *', value=date.today(), format='DD/MM/YYYY')
                with c2: hora_inicio = st.time_input('Horário de início *', value=time(8,0), step=1800)
                with c3: hora_termino = st.time_input('Horário de término *', value=time(9,0), step=1800)
                motivo = st.text_area('Motivo da reunião *', placeholder='Descreva o motivo da reunião...', height=105)
                c4,c5 = st.columns([1,1])
                with c4: data_show = st.radio('Vai precisar de data show?', ['Sim','Não'], horizontal=True)
                with c5: observacoes = st.text_area('Observações adicionais', placeholder='Informações opcionais...', height=90)
                enviar = st.form_submit_button('📅 SOLICITAR AGENDAMENTO', type='primary', use_container_width=True, disabled=not carregou)
            if enviar:
                if not responsavel.strip() or not motivo.strip():
                    st.error('Preencha o nome do responsável e o motivo da reunião.')
                elif data_reuniao < date.today():
                    st.error('Selecione uma data de hoje em diante.')
                elif hora_inicio >= hora_termino:
                    st.error('O horário de término deve ser posterior ao horário de início.')
                else:
                    with st.spinner('Verificando disponibilidade...'):
                        try:
                            atualizado = carregar_dados()
                            ini = hora_inicio.hour * 60 + hora_inicio.minute
                            fim = hora_termino.hour * 60 + hora_termino.minute
                            if tem_conflito(atualizado, data_reuniao.isoformat(), ini, fim):
                                st.error('A sala já está reservada nesse horário. Escolha outro período.')
                            else:
                                payload = {'Responsavel':responsavel.strip(),'Data':data_reuniao.isoformat(),
                                    'Hora_Inicio':hora_inicio.strftime('%H:%M'),'Hora_Termino':hora_termino.strftime('%H:%M'),
                                    'Sala':'Sala de Reuniões da Secretaria','Data_Show':data_show,
                                    'Motivo':motivo.strip(),'Observacoes':observacoes.strip()}
                                resposta = requests.post(WEB_APP_URL, json=payload, timeout=22)
                                resposta.raise_for_status()
                                texto = resposta.text.strip().lower()
                                if any(x in texto for x in ('error','erro','failed','falha')):
                                    st.error('O servidor retornou um erro ao salvar. Verifique a planilha antes de tentar novamente.')
                                else:
                                    st.success('Solicitação enviada! Confirme o registro na lista de reservas.')
                                    st.info('Caso não apareça imediatamente, atualize a página. A confirmação definitiva depende do retorno do Apps Script.')
                        except (requests.RequestException, ValueError) as exc:
                            st.error(f'Não foi possível concluir a solicitação: {exc}')
            st.markdown('<div class="note">Se precisar do data show, faça também o agendamento na Coordenação do Núcleo de Tecnologia.</div>', unsafe_allow_html=True)
    with col_right:
        with st.container(border=True):
            st.markdown('<div class="section-title">📅 Calendário de Reservas</div>', unsafe_allow_html=True)
            mes_ref = date.today()
            mes_escolhido = st.date_input('Selecione o mês', value=mes_ref, format='DD/MM/YYYY', key='cal_inicio')
            st.markdown(f'**{MESES[mes_escolhido.month]} de {mes_escolhido.year}**')
            st.markdown(calendario_html(mes_escolhido.year, mes_escolhido.month, set(df['Data_Normalizada'])), unsafe_allow_html=True)
            st.caption('🟩 Dia com reserva · 🟠 Marcador de reunião · Contorno verde: hoje')
            st.caption('O calendário mostra dias com agendamentos, não disponibilidade por horário.')
        with st.container(border=True):
            st.markdown('<div class="section-title">🕘 Próximas Reuniões</div>', unsafe_allow_html=True)
            if validos.empty: st.info('Nenhuma reunião futura cadastrada.')
            else:
                for _, row in validos.head(5).iterrows(): render_reserva(row)

elif pagina == '📅 Calendário':
    with st.container(border=True):
        st.subheader('Calendário de Reservas')
        selecionado = st.date_input('Mês para consultar', value=date.today(), format='DD/MM/YYYY')
        st.markdown(f'### {MESES[selecionado.month]} de {selecionado.year}')
        st.markdown(calendario_html(selecionado.year, selecionado.month, set(df['Data_Normalizada'])), unsafe_allow_html=True)
        st.caption('Os dias destacados possuem pelo menos uma reserva; outros horários podem estar livres.')
        do_mes = df[df['Data_Normalizada'].str.startswith(f'{selecionado.year}-{selecionado.month:02d}')] if not df.empty else df
        for _, row in do_mes.sort_values(['Data_Normalizada','Inicio_Normalizado']).iterrows(): render_reserva(row)

elif pagina == '📋 Todas as Reservas':
    st.subheader('Todas as Reservas')
    if df.empty: st.info('Nenhuma reserva cadastrada.')
    else:
        inicio_filtro = st.date_input('Exibir reservas a partir de', value=date.today(), format='DD/MM/YYYY')
        filtrado = df[df['Data_Normalizada'] >= inicio_filtro.isoformat()].sort_values(['Data_Normalizada','Inicio_Normalizado'])
        st.caption(f'{len(filtrado)} reserva(s) encontrada(s)')
        for _, row in filtrado.iterrows(): render_reserva(row)

elif pagina == '📊 Relatórios':
    st.subheader('Relatórios de Agendamentos')
    if df.empty: st.info('Não há dados para gerar relatórios.')
    else:
        resumo = df.copy()
        resumo['Mês'] = resumo['Data_Normalizada'].str.slice(0,7)
        st.bar_chart(resumo.groupby('Mês').size().rename('Reservas'))
        csv = df[COLUNAS].to_csv(index=False).encode('utf-8-sig')
        st.download_button('📥 Exportar reservas em CSV', csv, file_name='reservas_semed.csv', mime='text/csv')

st.markdown('<div class="footer">Secretaria Municipal de Educação · Núcleo de Tecnologias Educacionais</div>', unsafe_allow_html=True)
