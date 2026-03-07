import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.express as px
import pandas as pd
import sqlite3
from datetime import datetime

# Cria o aplicativo
app = dash.Dash(__name__)

# Layout da página
app.layout = html.Div(style={'font-family': 'Arial, sans-serif', 'padding': '20px'}, children=[
    html.H1("Dashboard - Usina do Conhecimento", style={'textAlign': 'center'}),
    
    # 1. Seletor de Data
    html.Div([
        html.Label("Selecione a data: ", style={'fontSize': '18px', 'fontWeight': 'bold', 'marginRight': '10px'}),
        dcc.DatePickerSingle(
            id='seletor-data',
            date=datetime.now().date(), # Começa selecionando o dia de hoje
            display_format='DD/MM/YYYY',
            style={'marginBottom': '20px'}
        )
    ], style={'textAlign': 'center'}),
    
    # 2. Painel de totais no topo
    html.Div(id='kpis', style={'textAlign': 'center', 'fontSize': '26px', 'marginBottom': '30px'}),
    
    # 3. Gráfico de barras
    dcc.Graph(id='grafico-fluxo'),

    dcc.Interval(id='intervalo-atualizacao', interval=5000, n_intervals=0)
])

# Função para atualizar os dados quando muda a data ou a cada 5 segundos
@app.callback(
    [Output('kpis', 'children'), Output('grafico-fluxo', 'figure')],
    [Input('seletor-data', 'date'),
     Input('intervalo-atualizacao', 'n_intervals')]
)
def atualizar_dashboard(data_selecionada, n):
    conn = sqlite3.connect('usina_dados.db')
    query = f"SELECT * FROM fluxo_pessoas WHERE data_hora LIKE '{data_selecionada}%'"
    df = pd.read_sql_query(query, conn)
    conn.close()

    data_br = datetime.strptime(data_selecionada, '%Y-%m-%d').strftime('%d/%m/%Y')

    # Se não houver movimento no dia selecionado
    if df.empty:
        texto_kpi = html.Div([
            html.Span("Total de entradas: 0", style={'color': '#00CC96', 'marginRight': '40px', 'fontWeight': 'bold'}),
            html.Span("Total de saídas: 0", style={'color': '#EF553B', 'fontWeight': 'bold'})
        ])
        fig = px.bar(title=f"Sem movimento registrado no dia {data_br}.")
        return texto_kpi, fig

    df['data_hora'] = pd.to_datetime(df['data_hora'])
    
    entradas_totais = len(df[df['evento'] == 'Entrada'])
    saidas_totais = len(df[df['evento'] == 'Saida'])
    
    # Monta o texto visual do topo
    texto_kpi = html.Div([
        html.Span(f"Total de entradas: {entradas_totais}", style={'color': '#00CC96', 'marginRight': '40px', 'fontWeight': 'bold'}),
        html.Span(f"Total de saídas: {saidas_totais}", style={'color': '#EF553B', 'fontWeight': 'bold'})
    ])

    df['hora'] = df['data_hora'].dt.hour
    
    # Agrupa contando quantas entradas e saídas houveram em cada hora
    resumo_hora = df.groupby(['hora', 'evento']).size().reset_index(name='quantidade')
    
    # Cria o gráfico de barras
    fig = px.bar(
        resumo_hora, 
        x='hora', 
        y='quantidade', 
        color='evento', 
        barmode='group', 
        title=f"Fluxo por hora - {data_br}",
        labels={'hora': 'Hora do dia (0h - 23h)', 'quantidade': 'Número de pessoas', 'evento': 'Ação'},
        color_discrete_map={'Entrada': '#00CC96', 'Saida': '#EF553B'}
    )
    
    fig.update_layout(
        xaxis=dict(tickmode='linear', tick0=0, dtick=1, range=[-0.5, 23.5]),
        plot_bgcolor='white'
    )

    return texto_kpi, fig

if __name__ == '__main__':
    # Permite acessar de qualquer dispositivo na mesma rede
    app.run(debug=True, host='0.0.0.0', port=8050)