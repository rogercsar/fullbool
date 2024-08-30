from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters as tg_filters, CallbackContext
from pyfutebol import crawler
from datetime import datetime
import os
import wikipedia
import calendar
import json
import logging
import time
import requests
from GoogleNews import GoogleNews

from bd import *

API_KEY = '7ec1ae1461da5ec0324095bd682667d7'

# Configura o logger para capturar as exceções
logging.basicConfig(level=logging.INFO)

# Configurando a língua da Wikipedia
wikipedia.set_lang("pt")

def get_wikipedia_summary(query):
    try:
        page = wikipedia.page(query)
        return page.summary
    except wikipedia.DisambiguationError as e:
        return f"Nia: Retornou múltiplos resultados: {e.options}."
    except wikipedia.PageError:
        return f"Nia: Não foi possível encontrar uma página para '{query}'."
    except Exception as e:
        return f"Ocorreu um erro ao buscar na Wikipedia: {e}."
    
# Função para gerar calendário
def generate_calendar(year, month=None):
    cal = calendar.TextCalendar(calendar.SUNDAY)
    if month:
        try:
            month_calendar = cal.formatmonth(year, month)
            return f"```\n{month_calendar}\n```"
        except calendar.IllegalMonthError:
            return "Por favor, forneça um mês válido (1-12)."
    else:
        year_calendar = ''
        for month in range(1,13):
            year_calendar += cal.formatmonth(year, month)
            year_calendar += '\n\n'
        return f"```\n{year_calendar}\n```"
    
# Processa a entrada do usuário e armazena na memória
def process_user_input(frase):
    user_input = frase.casefold()
       
    if 'wiki' in user_input or 'me fale sobre' in user_input or 'o que você sabe sobre' in user_input:
        query = user_input.replace('wiki', '').replace('me fale sobre', '').replace('o que você sabe sobre', '').strip()
        if query:
            return get_wikipedia_summary(query)
        else:
            return "Por favor, forneça um termo para pesquisar na Wikipedia."
        
def split_message(message, max_length=4096):
    """Divide uma mensagem em partes menores com base no comprimento máximo permitido pelo Telegram."""
    return [message[i:i + max_length] for i in range(0, len(message), max_length)]
        
# Função de inicialização do bot
async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Olá! Eu sou FullBool. Como posso ajudar você hoje?')

# Função para responder mensagens
async def respond(update: Update, context: CallbackContext) -> None:
    frase = update.message.text

    try:
        #Consulta na wikipédia 
        if 'wiki' in frase.casefold() or 'me fale sobre' in frase.casefold() or 'o que você sabe sobre' in frase.casefold():
            response = process_user_input(frase.casefold())
            await update.message.reply_text(response)

        #Mostra a hora atual 
        elif 'que horas são' in frase.casefold():
            current_time = datetime.now().strftime("%H:%M:%S")
            await update.message.reply_text(f"São {current_time}.")

        #Mostra a data atual 
        elif 'que dia é hoje' in frase.casefold():
            current_date = datetime.now().strftime("%d/%m/%Y")
            await update.message.reply_text(f"Hoje é {current_date}.")

        #Gera calendário do ano ou do mês específico 
        elif 'calendário do ano de' in frase.casefold():
            try:
                parts = frase.split('calendário do ano de')[-1].strip().split()
                year = int(parts[0])
                
                if len(parts) > 1:
                    month_str = parts[1]
                    if month_str.isdigit():
                        month = int(month_str)
                    else:
                        month_map = {
                            'janeiro': 1, 'fevereiro': 2, 'março': 3, 'abril': 4,
                            'maio': 5, 'junho': 6, 'julho': 7, 'agosto': 8,
                            'setembro': 9, 'outubro': 10, 'novembro': 11, 'dezembro': 12
                        }
                        month = month_map.get(month_str.lower())

                    if month:
                        response = generate_calendar(year, month)
                        await update.message.reply_text(response)
                    else:
                        response = "Por favor, forneça um mês válido (1-12 ou nome do mês em português)."
                else:
                    response = generate_calendar(year)
                    await update.message.reply_text(response)
                
            except (ValueError, IndexError):
                await update.message.reply_text("Por favor, forneça um ano válido e, opcionalmente, um mês (1-12 ou nome do mês em português).")

        #Consulta tempo atual na cidade 
        elif 'tempo hoje em' in frase.casefold() or 'clima hoje em' in frase.casefold(): 
            list_cidade = None      
            try:     
                for cidade in cidades:
                    if cidade.casefold() in frase.casefold():
                        list_cidade = cidade
                        break
                if list_cidade:
                    city = frase.split(list_cidade, 1)
                    city_name = list_cidade
                elif not city:
                    await update.message.reply_text("Por favor, forneça o nome da cidade.")
                    return
                link = f"https://api.openweathermap.org/data/2.5/weather?q={city_name}&appid={API_KEY}&lang=pt_br"
                req = requests.get(link)
                req_dic = req.json()
                if req.status_code == 200:
                    desc = req_dic['weather'][0]['description']
                    temp = req_dic['main']['temp'] - 273.15  # Convertendo de Kelvin para Celsius
                    clima = [f"Cidade: {city_name}", f"Descrição: {desc}", f"Temperatura: {temp:.2f}°C"]
                    
                    def format_list_as_string(items):
                        return "\n".join([f"- {item}" for item in items])
                    
                    prev = format_list_as_string(clima)
                    await update.message.reply_text(f"{prev}")
                else:
                    await update.message.reply_text("Não consegui encontrar a previsão para essa cidade. Verifique o nome e tente novamente.")
            except Exception as e:
                await update.message.reply_text(f"Ocorreu um erro ao buscar a previsão do tempo: {str(e)}.")

        #Conversão de moedas 
        elif 'converter de' in frase.casefold():
            list_md = None
            try:
                for i in list_moedas:
                    if i.casefold() in frase.casefold():
                        list_md = i
                        break

                if list_md:
                    # Constrói a URL da API para o par de moedas encontrado
                    url_api = f'https://economia.awesomeapi.com.br/last/{list_md}'
                    # Realiza a solicitação à API
                    req = requests.get(url_api)
                    # Processa a resposta da API
                    conversao = req.json()

                    # Extração dos dados relevantes da resposta
                    moeda_base, moeda_cotacao = list_md.split('-')
                    key = f"{moeda_base}{moeda_cotacao}"
                    if key in conversao:
                        info_moeda = conversao[key]
                        valor = info_moeda['bid']
                        resposta = f"1 {moeda_base} é igual a {valor} {moeda_cotacao}."

                        # Adiciona a resposta na sessão do Streamlit
                        await update.message.reply_text(f"{resposta}.")
                    else:
                        await update.message.reply_text(f"Não foi possível obter a conversão solicitada.")
                else:
                    await update.message.reply_text(f"Moeda não encontrada na lista de moedas suportadas.")
            
            except Exception as e:
                await update.message.reply_text(f"Ocorreu um erro ao converter as moedas: {str(e)}.")   

        #Consulta notícias 
        elif 'notícias' in frase.casefold():
            list_nt = None      
            try:     
                for i in list_noticias:
                    if i.casefold() in frase.casefold():
                        list_nt = i
                        break
                if list_nt:
                    word = frase.split(list_nt, 1)
                    word_nt = list_nt               
                    googleNews = GoogleNews(period='d')
                    googleNews.set_lang('pt')
                    googleNews.search(word_nt)
                    result = googleNews.result()

                    # Formatar os resultados como uma lista de strings
                    news_list = [f"Title: {item['title']}\nConteúdo: {item.get('desc', 'N/A')}\nData: {item.get('date', 'N/A')}\nLink: {item['link']}" for item in result]
                    formatted_news = "\n\n".join(news_list)
                    
                    # Dividir a mensagem longa em partes menores
                    messages = split_message(formatted_news)
                    
                    # Enviar cada parte da mensagem separadamente
                    for message in messages:
                        await update.message.reply_text(message)
                
                else:
                    await update.message.reply_text(f"Por favor, forneça o termo válido para pesquisa.")
                    return

            except Exception as e:
                await update.message.reply_text(f"Ocorreu um erro ao buscar a notícia: {str(e)}.")

        
        #Consulta jogos do dia 
        elif 'jogos de hoje' in frase.casefold() or 'as partidas de hoje' in frase.casefold():
            resultados = crawler.jogos_de_hoje()
            for resultado in resultados:
                try:
                    data = resultado
                    partida = data['match']
                    periodo = data['status']
                    campeonato = data['league']
                    # Verifica se scoreboard é um dicionário e acessa as informações dos times
                    scoreboard = data.get('scoreboard', {})
                    if isinstance(scoreboard, dict):
                        # Obtemos os times e os pontos
                        times = list(scoreboard.keys())
                        if len(times) == 2:
                            time1 = times[0]
                            time2 = times[1]
                            placar_time1 = scoreboard.get(time1, '0')
                            placar_time2 = scoreboard.get(time2, '0')
                            placar = f"{time1} {placar_time1} - {time2} {placar_time2}"
                        else:
                            placar = 'Placar não disponível'
                    else:
                        placar = 'Placar não disponível'

                    result = data.get('summary', 'Resumo não disponível')
                    jogo = (
                            f"Partida: {partida}\n" 
                            f"Período: {periodo}\n"
                            f"Campeonato: {campeonato}\n" 
                            f"Placar: {placar}\n" 
                            f"Resultado: {result}"
                            )
                    await update.message.reply_text(jogo)
                except KeyError as e:
                    await update.message.reply_text(f"Erro: A chave {e} não foi encontrada no JSON.")

        #Consulta jogos ao vivo 
        elif 'jogos ao vivo' in frase.casefold() or 'as partidas ao vivo' in frase.casefold():
            resultados = crawler.jogos_ao_vivo()        
            for resultado in resultados:
                try:
                    data = resultado
                    partida = data['match']
                    periodo = data['status']
                    campeonato = data['league']
                    # Verifica se scoreboard é um dicionário e acessa as informações dos times
                    scoreboard = data.get('scoreboard', {})
                    if isinstance(scoreboard, dict):
                        # Obtemos os times e os pontos
                        times = list(scoreboard.keys())
                        if len(times) == 2:
                            time1 = times[0]
                            time2 = times[1]
                            placar_time1 = scoreboard.get(time1, '0')
                            placar_time2 = scoreboard.get(time2, '0')
                            placar = f"{time1} {placar_time1} - {time2} {placar_time2}"
                        else:
                            placar = 'Placar não disponível'
                    else:
                        placar = 'Placar não disponível'

                    result = data.get('summary', 'Resumo não disponível')

                    jogo = (
                            f"Partida: {partida}\n"
                            f"Período: {periodo}\n"
                            f"Campeonato: {campeonato}\n"
                            f"Placar: {placar}\n"
                            f"Resultado: {result}"
                            )
                    await update.message.reply_text(jogo)
                except KeyError as e:
                    await update.message.reply_text(f"Erro: A chave {e} não foi encontrada no JSON.")
            
        #Consulta jogos pelo time ou informações do time da wikipedia 
        elif any(word in list_times for word in frase.casefold().strip().split(" ")):
            time = frase.capitalize().split('jogo do')[-1].strip()
            await update.message.reply_text(
                "Você gostaria de saber sobre o time na Wikipedia ou os jogos? Responda com wikipedia ou jogos."
            )
            if frase.casefold() == 'wikipedia':
                response = process_user_input(frase.casefold())
                await update.message.reply_text(response)
            
            elif frase.casefold() == 'jogos':
                resultados = crawler.buscar_jogo_por_time(time)    
                for resultado in resultados:   
                    try:
                        data = resultado
                        partida = data['match']
                        periodo = data['status']
                        campeonato = data['league']
                        # Verifica se scoreboard é um dicionário e acessa as informações dos times
                        scoreboard = data.get('scoreboard', {})
                        if isinstance(scoreboard, dict):
                            # Obtemos os times e os pontos
                            times = list(scoreboard.keys())
                            if len(times) == 2:
                                time1 = times[0]
                                time2 = times[1]
                                placar_time1 = scoreboard.get(time1, '0')
                                placar_time2 = scoreboard.get(time2, '0')
                                placar = f"{time1} {placar_time1} - {time2} {placar_time2}"
                            else:
                                placar = 'Placar não disponível'
                        else:
                            placar = 'Placar não disponível'

                        result = data.get('summary', 'Resumo não disponível')
                        jogo = (
                                f"Partida: {partida}\n" 
                                f"Período: {periodo}\n" 
                                f"Campeonato: {campeonato}\n" 
                                f"Placar: {placar}\n"
                                f"Resultado: {result}"
                                )
                        await update.message.reply_text(jogo)
                    except KeyError as e:
                        await update.message.reply_text(f"Erro: A chave {e} não foi encontrada no JSON.") 
    except KeyError as e:
        logging.warning(f"Chave não encontrada: {e}")
        await update.message.reply_text(f"Erro: Informação não disponível.")
    except Exception as e:
        logging.error(f"Erro inesperado: {e}", exc_info=True)
        await update.message.reply_text("Desculpe, ocorreu um erro inesperado. Tente novamente mais tarde.")

def main() -> None:
    # Substitua 'YOUR_TELEGRAM_TOKEN_HERE' pelo token do seu bot
    application = Application.builder().token("6820426627:AAH44HX4sxYXc_i40KtPBhL85epPbdYNec4").build()

    # Comandos
    application.add_handler(CommandHandler("start", start))

    # Mensagens
    application.add_handler(MessageHandler(tg_filters.TEXT & ~tg_filters.COMMAND, respond))

    # Iniciar o bot
    application.run_polling()

if __name__ == '__main__':
    main()

  