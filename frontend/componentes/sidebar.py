import streamlit as st

def renderizar_sidebar(salas):
    """
    Renderiza a sidebar e retorna o limite da sensação térmica desejado
    e a sala escolhida.
    """

    st.sidebar.title("Configurações")

    # Sala a exibir (sala 1: placa real; sala 2: simulador)
    sala = st.sidebar.selectbox(
            "Sala",
            salas or ["1"],
            format_func=lambda s: f"Sala {s}"
        )
    
    st.sidebar.subheader("Limites de conforto")

    # Limite de sensação térmica
    limite_sensacao_maximo= st.sidebar.number_input(
            "Sensação térmica (°C)",
            min_value=0.0,
            max_value=60.0,
            value=30.0,
            step=0.5
        )
    

    return limite_sensacao_maximo, sala