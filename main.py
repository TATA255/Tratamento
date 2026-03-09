import pyautogui             # Biblioteca para controlar teclado/mouse (automação de interface)
import pyperclip             # Biblioteca para ler/escrever texto na área de transferência (clipboard)
import time                  # Biblioteca para pausas (sleep) e controle de tempo

pyautogui.FAILSAFE = True    # Segurança: se você mover o mouse para o canto superior esquerdo,
                             # o PyAutoGUI para tudo com exceção (bom para interromper travamentos)


def extrair_dados_perfil(texto_bruto):
    # Recebe um texto "cru" (o que foi copiado da página inteira do LinkedIn)
    # e tenta extrair: nome, sobrenome, empresa, cargo, cidade e estado.

    linhas = [l.strip() for l in texto_bruto.split('\n') if len(l.strip()) > 1]
    # 1) texto_bruto.split('\n') -> quebra o texto em linhas
    # 2) l.strip() -> remove espaços no começo e no fim
    # 3) if len(l.strip()) > 1 -> mantém só linhas com pelo menos 2 caracteres (evita lixo vazio)
    # Resultado: "linhas" é uma lista limpa com as linhas do perfil.

    indice_exp = -1
    # Variável para guardar o índice onde começa a seção "experiência".
    # -1 significa "não encontrado".

    dados = {
        "empresa": "Não encontrado",    # valor padrão caso não ache empresa
        "nome": "Não encontrado",       # valor padrão caso não ache nome
        "sobrenome": "",                # padrão vazio
        "Cargo": "Não encontrado",      # valor padrão caso não ache cargo
        "Cidade": "Não encontrado",     # valor padrão caso não ache cidade
        "Estado": "Não encontrado",     # valor padrão caso não ache estado
    }
    # Esse dicionário é o que a função devolve no final.


    # --- 1. EXTRAÇÃO DO NOME (Lógica de Exclusão de Menus) ---
    # A ideia é: no texto copiado do LinkedIn, vêm muitas linhas do menu/topo.
    # Você tenta ignorar essas linhas "ruído" e pegar a primeira linha que pareça um nome.

    termos_bloqueados_topo = [
        "notificação", "início", "minha rede", "vagas", "mensagens",
        "notificações", "eu", "para negócios", "experimente",
        "premium", "brl0", "r$ 0", "pesquisar", "pular para o conteúdo",
        "conectar", "mensagem", "seguir", "pular", "conteúdo",
        "Atalhos do teclado", "Fechar menu pular"
    ]
    # Lista de palavras/trechos que, se aparecerem numa linha, indicam que a linha é do menu.
    # Detalhe importante: você faz linha_lower = linha.lower()
    # então os termos ideais aqui deveriam estar TODOS em minúsculo.
    # "Atalhos do teclado" e "Fechar menu pular" podem não bater porque têm maiúsculas.

    for i, linha in enumerate(linhas):
        # enumerate(linhas) dá (índice, conteúdo) para cada linha.
        # i = posição da linha
        # linha = conteúdo da linha

        linha_lower = linha.lower()
        # Converte a linha para minúsculo para comparar sem sensibilidade a maiúsculas.

        if not any(termo in linha_lower for termo in termos_bloqueados_topo) and len(linha) > 2:
            # any(...) retorna True se QUALQUER termo bloqueado aparecer dentro da linha.
            # not any(...) então significa: "nenhum termo bloqueado apareceu".
            # len(linha) > 2 evita pegar linhas muito curtas.

            nome_candidato = linha.strip()
            # Remove espaços da linha candidata.

            if not any(char.isdigit() for char in nome_candidato):
                # Se tiver número no "nome", provavelmente não é um nome real (ex: "R$ 0", "2024" etc).
                # Se NÃO tiver número, você aceita.

                partes = nome_candidato.split(' ')
                # Quebra o nome por espaços.
                # Ex: "João Silva Souza" -> ["João", "Silva", "Souza"]

                dados["nome"] = partes[0]
                # Primeiro termo vai para "nome": "João"

                dados["sobrenome"] = " ".join(partes[1:]) if len(partes) > 1 else ""
                # Junta o resto como sobrenome: "Silva Souza"
                # Se só tiver 1 parte, sobrenome vira "".

                break
                # Para o loop assim que encontrar o primeiro "nome válido".


    # --- 2. EXTRAÇÃO DA EMPRESA (Busca na Experiência) ---
    indice_exp = -1
    # Recomeça o índice da experiência (reset).

    for i, linha in enumerate(linhas):
        if linha.lower() == "experiência":
            # Procura a linha que seja exatamente "experiência" (em minúsculo).
            # Se achar, marca o índice para saber onde começa a seção.

            indice_exp = i
            break
            # Para ao encontrar a primeira ocorrência.

    if indice_exp != -1:
        # Se achou a seção experiência...

        for i in range(indice_exp + 1, len(linhas)):
            # Percorre todas as linhas depois de "experiência".

            candidato = linhas[i]
            # Linha candidata a ser empresa.

            termos_bloqueados = [
                'exibir', 'notificação', 'vaga', 'moment',
                'diretor', 'director', 'gerente', 'manager',
                'tempo integral', 'híbrido'
            ]
            # Termos para evitar pegar ruídos (botões, cargos genéricos, status etc).
            # Observação: bloquear "diretor/gerente" pode fazer você
            # PULAR linhas úteis dependendo do layout.

            if not any(t in candidato.lower() for t in termos_bloqueados) and \
               not any(char.isdigit() for char in candidato[:2]):
                # Condição 1: não pode ter termos bloqueados.
                # Condição 2: não pode começar com dígitos nos primeiros 2 caracteres
                # (evita linhas do tipo "2022", "1 ano", etc).

                dados["empresa"] = candidato.split('·')[0].strip()
                # Divide no ponto médio '·' (muito comum no LinkedIn)
                # e pega só a parte antes do '·'. Depois dá strip().

                break
                # Para na primeira empresa "plausível".


    # --- 3 e 4. EXTRAÇÃO DO CARGO (com âncora "o momento") ---
    if indice_exp != -1:
        # Se existe seção "experiência"...

        encontrou_cargo = False
        # Flag para saber se encontrou cargo no Plano A.

        # PLANO A: perfis onde aparece "o momento" (muito comum em experiência atual)
        for i in range(indice_exp + 1, len(linhas)):
            if "o momento" in linhas[i].lower():
                # Achou a âncora "o momento" -> usa isso como referência.

                ruido = ["tempo integral", "terceirizado", "híbrido", "remoto", "presencial"]
                # Lista de ruídos comuns logo perto do cargo.

                # Sobe buscando o cargo (pula ruídos e a linha com '·')
                for j in range(1, 4):
                    # Vai olhar as 3 linhas ACIMA da linha "o momento".
                    # j=1 => linha imediatamente acima, j=2 => duas linhas acima...

                    candidato = linhas[i-j]
                    # Seleciona a linha anterior.

                    if not any(r in candidato.lower() for r in ruido) and "·" not in candidato:
                        # Se não é ruído e não tem o caractere '·', considera isso como cargo.

                        dados["Cargo"] = candidato
                        # Salva como cargo.

                        encontrou_cargo = True
                        # Marca que achou.

                        break
                        # Para de procurar cargo.

                # A empresa geralmente está no "Logo da empresa" ou acima do cargo
                for k in range(i, indice_exp, -1):
                    # Varre para cima (de i até indice_exp) procurando "logo da empresa".

                    if "logo da empresa" in linhas[k].lower():
                        # Se encontrar a linha com "logo da empresa", tenta extrair o nome.

                        dados["empresa"] = linhas[k].lower().replace("logo da empresa", "").strip().title()
                        # Remove o texto "logo da empresa", tira espaços e coloca Title Case.

                        break

                break
                # Para o loop principal depois de tratar o Plano A.


        # PLANO B: se não achou "o momento", tenta heurística simples
        if not encontrou_cargo:
            # O cargo costuma ser a primeira linha após "Experiência",
            # e a empresa a segunda linha (depende do layout do conteúdo copiado).

            if indice_exp + 1 < len(linhas):
                dados["Cargo"] = linhas[indice_exp + 1]
                # Pega a primeira linha depois de "experiência" como cargo.

            if indice_exp + 2 < len(linhas):
                dados["empresa"] = linhas[indice_exp + 2]
                # Pega a segunda linha depois como empresa.
                # (Isso pode pegar errado se a estrutura do perfil variar.)


    # --- 5. CIDADE E ESTADO (Busca no Topo do Perfil) ---
    for i, linha in enumerate(linhas):
        # Procura dentro de todas as linhas.

        if "brasil" in linha.lower() and "," in linha:
            # Heurística: localização costuma conter "Brasil" e vírgulas
            # Ex: "São Paulo, São Paulo, Brasil"

            if not any(mes in linha.lower() for mes in ["jan", "fev", "mar", "abr", "mai", "jun",
                                                       "jul", "ago", "set", "out", "nov", "dez", "momento"]):
                # Filtro: não pode conter meses nem "momento", para evitar confundir com datas da experiência.

                local_limpo = linha.split('·')[0].strip()
                # Remove o que vier depois do '·' (ex: "· Dados de contato")

                partes_local = local_limpo.split(',')
                # Separa cidade/estado/país por vírgula.

                if len(partes_local) >= 2:
                    dados["Cidade"] = partes_local[0].strip()
                    # Primeira parte vira cidade.

                    estado_bruto = partes_local[1].strip()
                    # Segunda parte vira estado (normalmente).

                    dados["Estado"] = estado_bruto.replace(" Brasil", "").strip()
                    # Remove " Brasil" se estiver grudado.

                    break
                    # Para ao achar a primeira localização válida.

                else:
                    dados["Cidade"] = local_limpo
                    # Caso não tenha vírgula suficiente, joga tudo em Cidade.

                    break

    return dados
    # Devolve o dicionário final com o que conseguiu extrair.



def extrair_dados_lusha(dados_brutos):
    # Recebe o texto copiado da tela do Lusha e tenta extrair email e telefones.

    linhas = [l.strip() for l in dados_brutos.split('\n') if len(l.strip()) > 1]
    # Mesma lógica: quebra em linhas, tira espaços, remove linhas vazias.

    informacoes = {
        "telefone": "Não encontrado",
        "celular": "Não encontrado",
        "email": "Não encontrado"
    }
    # Dicionário de retorno.

    telefones_encontrados = []
    # Lista para guardar números que pareçam telefone.

    for linha in linhas:
        # Varre cada linha copiada do Lusha.

        # --- 1. EXTRAÇÃO DE E-MAIL (Âncora: @) ---
        if "@" in linha and " " not in linha:
            # Se tem @ e não tem espaço, assume que a linha é só um e-mail.
            # (Pode falhar se vier "Email: x@y.com" porque tem espaço.)

            informacoes["email"] = linha.lower().strip()
            # Salva em minúsculo.

        # --- 2. EXTRAÇÃO DE NÚMEROS (Âncora: +) ---
        if "+" in linha:
            # Se tem +, assume que é telefone (formato internacional normalmente começa com +).

            numero_candidato = linha.strip()
            # Remove espaços.

            if sum(c.isdigit() for c in numero_candidato) >= 10:
                # Conta quantos dígitos existem.
                # Se tiver pelo menos 5 dígitos, considera telefone.

                telefones_encontrados.append(numero_candidato)
                # Adiciona na lista.

    # --- 3. ATRIBUIÇÃO DOS NÚMEROS ENCONTRADOS ---
    if len(telefones_encontrados) >= 1:
        informacoes["celular"] = telefones_encontrados[0]
        # Primeiro número encontrado vira "celular".

    if len(telefones_encontrados) >= 2:
        informacoes["telefone"] = telefones_encontrados[1]
        # Segundo número vira "telefone".

    return informacoes
    # Devolve email/celular/telefone.



def executar_automacao():
    # Função principal: controla navegador/planilha, copia dados e preenche a linha.

    print("--- INICIANDO EM 5 SEGUNDOS ---")
    # Mensagem para você se preparar (mudar foco, abrir abas, etc).

    time.sleep(5)
    # Espera 5 segundos antes de começar.

    for _ in range(2):
        # Loop principal: repete 3 vezes (processa 3 linhas/perfis).
        # "_" é usado porque você não precisa do valor do contador.

        # --- PASSO 1: PEGAR LINK NA COLUNA J ---
        pyautogui.hotkey('ctrl', '1')
        # No navegador (ex: Chrome), Ctrl+1 muda para a 1ª aba.
        # Você está assumindo que na aba 1 está sua planilha.

        time.sleep(0.5)
        # Pequena pausa para a troca de aba ocorrer.

        pyautogui.press('home')
        # Pressiona Home. Em planilhas/web pode levar ao começo da linha/célula.
        # Na prática isso depende do foco estar dentro da grade da planilha.

        for _ in range(9):
            pyautogui.press('tab')
        # Dá 9 TABs para chegar até a coluna J (ou a célula desejada).
        # Isso só funciona se:
        # - o cursor começar na coluna certa
        # - a tabulação seguir a ordem esperada

        pyperclip.copy('')
        # Zera o clipboard (boa prática para não reutilizar conteúdo velho).

        pyautogui.hotkey('ctrl', 'c')
        # Copia o conteúdo da célula atual (onde você acha que está o link).

        time.sleep(0.8)
        # Espera o clipboard atualizar.

        url = pyperclip.paste().strip()
        # Lê do clipboard e remove espaços.
        # "url" deve virar o link do perfil.

        if url.startswith("http"):
            # Só continua se o valor copiado parecer um link.

            # --- PASSO 2: ACESSAR LINKEDIN ---
            pyautogui.hotkey('ctrl', '2')
            # Vai para a 2ª aba do navegador.
            # Você está assumindo que a aba 2 é LinkedIn.

            time.sleep(0.5)

            pyautogui.hotkey('ctrl', 'l')
            # Ctrl+L foca a barra de endereços do navegador.

            pyperclip.copy(url)
            # Coloca a URL no clipboard.

            pyautogui.hotkey('ctrl', 'v')
            # Cola a URL na barra de endereços.

            time.sleep(15)
            # Pausa antes de apertar Enter (provavelmente desnecessária,
            # mas você pode ter colocado para garantir que a cola terminou/estabilizou).

            pyautogui.press('enter')
            # Navega para a URL.

            time.sleep(10)
            # Espera carregar.

            pyautogui.press('pgdn')
            # PageDown: rola a página para baixo (pode “ativar” carregamento de elementos).

            time.sleep(10)

            pyautogui.hotkey('ctrl', 'a')
            # Seleciona tudo da página (depende do navegador/elemento focado).

            pyautogui.hotkey('ctrl', 'c')
            # Copia a seleção (conteúdo textual visível + alguns textos de UI).

            time.sleep(10)
            # Espera garantir que o conteúdo foi copiado.

            info = extrair_dados_perfil(pyperclip.paste())
            # Lê o texto copiado do clipboard e chama sua função que extrai:
            # nome/sobrenome/empresa/cargo/cidade/estado

            pyautogui.moveTo(-177, 665, duration=1.0)
            # Move o mouse para a posição x=-177, y=665 em 1 segundo.
            # Importante: x negativo significa "fora do monitor principal para a esquerda".
            # Isso normalmente só faz sentido se você tiver segundo monitor ou coordenadas específicas.

            pyautogui.click()
            # Clica nesse ponto. Você está assumindo que nesse local está o painel/campo do Lusha.

            time.sleep(15)
            # Espera carregar/abrir o painel.

            pyautogui.hotkey('ctrl', 'a')
            # Seleciona tudo do painel/campo focado.

            pyautogui.hotkey('ctrl', 'c')
            # Copia tudo.

            info_lusha = extrair_dados_lusha(pyperclip.paste())
            # Extrai email/telefone/celular a partir do texto copiado do Lusha.

            time.sleep(10)

            # --- PASSO 3: PREENCHIMENTO NA PLANILHA ---
            pyautogui.hotkey('ctrl', '1')
            # Volta para a aba 1 (planilha).

            time.sleep(0.5)

            # COLUNA A - Empresa
            pyautogui.press('home')
            # Volta para o início da linha/célula.

            pyautogui.press('delete')
            # Apaga o conteúdo da célula atual.

            pyperclip.copy(info["empresa"])
            # Coloca a empresa no clipboard.

            pyautogui.hotkey('ctrl', 'v')
            # Cola na célula.

            # COLUNA B - Nome
            pyautogui.press('tab')
            # Vai para próxima célula (coluna B).

            pyautogui.press('delete')
            # Limpa a célula.

            pyperclip.copy(info["nome"])
            # Copia o nome para o clipboard.

            pyautogui.hotkey('ctrl', 'v')
            # Cola o nome.

            # COLUNA C - Sobrenome
            pyautogui.press('tab')
            # Vai para coluna C.

            pyautogui.press('delete')

            pyperclip.copy(info["sobrenome"])
            # Copia sobrenome.

            pyautogui.hotkey('ctrl', 'v')
            # Cola sobrenome.

            print(f"✅ Processado: {info['nome']} | Empresa: {info['empresa']}")
            # Log no terminal do que foi processado.

            pyautogui.press('tab')
            # Próxima coluna (D, pelo seu fluxo).

            pyperclip.copy(info_lusha["email"])
            # Copia email do Lusha.

            pyautogui.hotkey('ctrl', 'v')
            # Cola email.

            pyautogui.press('tab')
            # Próxima coluna.

            pyperclip.copy(info_lusha["telefone"])
            # Copia telefone.

            pyautogui.hotkey('ctrl', 'v')
            # Cola telefone.

            pyautogui.press('tab')
            # Próxima coluna.

            pyperclip.copy(info_lusha["celular"])
            # Copia celular.

            pyautogui.hotkey('ctrl', 'v')
            # Cola celular.

            pyautogui.press('tab')
            # Próxima coluna (a do cargo).

            pyautogui.press('delete')
            # Limpa célula do cargo.

            pyperclip.copy(info.get("Cargo","Não encontrado"))
            # Pega o valor de "Cargo" no dicionário.
            # .get(...) evita KeyError se não existir a chave.
            # Se não tiver, usa "Não encontrado".

            pyautogui.hotkey('ctrl', 'v')
            # Cola o cargo.

            pyautogui.press('tab')
            # Próxima coluna (Estado).

            pyautogui.press('delete')
            # Limpa.

            pyperclip.copy(info["Estado"])
            # Copia estado.

            pyautogui.hotkey('ctrl', 'v')
            # Cola estado.

            time.sleep(0.2)
            # Pausa curta.

            pyautogui.press('tab')
            # Próxima coluna (Cidade).

            pyautogui.press('delete')

            pyperclip.copy(info["Cidade"])
            # Copia cidade.

            pyautogui.hotkey('ctrl', 'v')
            # Cola cidade.

            time.sleep(0.2)

        # PRÓXIMA LINHA
        pyautogui.press('home')
        # Volta para o início da linha.

        pyautogui.press('down')
        # Desce uma linha na planilha (próximo registro).

        time.sleep(8)
        # Espera (para evitar ir rápido demais / garantir que foco ficou correto).



if __name__ == "__main__":
    # Ponto de entrada: esse bloco só roda quando você executa o arquivo diretamente.
    executar_automacao()
    # Chama a automação principal.
    

# teste de mensagem github