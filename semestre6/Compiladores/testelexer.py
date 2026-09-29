import string
import sys


class AutomatoeLexer:
    # Caracteres tratados como separadores de tokens (nunca fazem parte do alfabeto)
    SEPARADORES = {" ", "\t", "\n", "\r"}

    def __init__(self):
        self.palavras = []
        self.alfabeto = set()
        self.estados = set()
        self.finais = set()
        self.transicoes = {}  # mapa (estado origem, simbolo) -> set de estados destino
        self.inicial = "S"
        self.erro = "X"       # estado de erro (reservado, o gerador nunca o usa)
        self.inalcancaveis = set()
        self.mortos = set()
        self.gramatica = {}
        self._gerador_nomes = self._criar_gerador_nomes()

        # entrada do reconhecedor: as próprias linhas de tokens do arquivo do
        # autômato, como (numero_da_linha, texto)
        self.entrada = []

        # saídas do reconhecedor
        self.fita = []               # ["E1", "E2", ..., "$"]
        self.tabela_simbolos = []    # [(linha, identificador, rotulo), ...]

    @staticmethod
    def _criar_gerador_nomes():
        # Gera nomes de estado como letras: A, B, C, ... Z, AA, BB, CC, ... ZZ, AAA, ...
        # sempre pulando S (estado inicial) e X (estado de erro), reservados.
        tamanho = 1
        while True:
            for letra in string.ascii_uppercase:
                if letra in ("S", "X"):
                    continue
                yield letra * tamanho
            tamanho += 1

    def _novo_estado(self):
        nome = next(self._gerador_nomes)
        self.estados.add(nome)
        return nome

    # ------------------------------------------------------------------
    # Construção do AFD (código original, com pequenos ajustes)
    # ------------------------------------------------------------------
    @staticmethod
    def _analisar_producao(producao):
        # Separa uma produção em (terminal, não-terminal destino).
        # Aceita "fA" e "f<A>" (terminal + NT), "f" (só terminal) e
        # "ε" / "epsilon" / "" (vazia -> (None, None)).
        if producao in ("ε", "", "epsilon"):
            return None, None

        simbolo = producao[0]
        resto = producao[1:].strip()

        if resto == "":
            return simbolo, None
        if resto.startswith("<") and resto.endswith(">"):
            resto = resto[1:-1]
        return simbolo, resto

    def carregar_palavras_e_gr(self, nome_arquivo):
        lendo_gramatica = False
        self.gramatica = {}

        with open(nome_arquivo, "r", encoding="utf-8") as arquivo:
            for numero_linha, linha in enumerate(arquivo, start=1):
                linha = linha.strip()
                if linha == "":
                    lendo_gramatica = True
                    continue

                if not lendo_gramatica:
                    # palavras reservadas
                    self.palavras.append(linha)
                    self.entrada.append((numero_linha, linha))
                    for letra in linha:
                        self.alfabeto.add(letra)

                else:  # GR
                    esquerda, direita = linha.split("::=")
                    esquerda = esquerda.strip()
                    direita = direita.strip()

                    # remove os símbolos < > do não-terminal à esquerda, ex: "<S>" -> "S"
                    if esquerda.startswith("<") and esquerda.endswith(">"):
                        esquerda = esquerda[1:-1]

                    producoes = []  # formato "a<Y>" ou "b<Z>" ou "ε"

                    for producao in direita.split("|"):
                        producao = producao.strip()
                        producoes.append(producao)

                        simbolo, _ = self._analisar_producao(producao)
                        if simbolo is not None:
                            self.alfabeto.add(simbolo)

                    self.gramatica[esquerda] = producoes

    def construir_automato_palavras(self):
        self.estados.add(self.inicial)

        for palavra in self.palavras:
            estado_atual = self.inicial

            for letra in palavra:
                chave = (estado_atual, letra)

                if chave not in self.transicoes:
                    novo = self._novo_estado()
                    self.transicoes[chave] = {novo}

                estado_atual = next(iter(self.transicoes[chave]))

            self.finais.add(estado_atual)

    def construir_automato_gramatica_regular(self):
        if not self.gramatica:
            return

        mapa_nao_terminal = {}
        for nao_terminal in self.gramatica:
            if nao_terminal == "S":
                mapa_nao_terminal[nao_terminal] = self.inicial
            else:
                mapa_nao_terminal[nao_terminal] = self._novo_estado()

        self.estados.add(self.inicial)

        for nao_terminal, producoes in self.gramatica.items():
            origem = mapa_nao_terminal[nao_terminal]

            for producao in producoes:
                simbolo, nao_terminal_destino = self._analisar_producao(producao)

                if simbolo is None:
                    # produção vazia -> este estado é final
                    self.finais.add(origem)
                    continue

                if nao_terminal_destino is not None:
                    destino = mapa_nao_terminal[nao_terminal_destino]
                else:
                    # produção só com terminal: termina a cadeia
                    destino = self._novo_estado()
                    self.finais.add(destino)

                chave = (origem, simbolo)
                self.transicoes.setdefault(chave, set()).add(destino)

    def determinizar(self):
        novos_estados = {}
        prox_estado = self._novo_estado
        mudou = True
        while mudou:
            mudou = False

            for chave in list(self.transicoes.keys()):
                destinos = self.transicoes[chave]
                if len(destinos) <= 1:
                    continue

                conjunto = frozenset(destinos)
                if conjunto not in novos_estados:
                    novo = prox_estado()
                    novos_estados[conjunto] = novo

                    for simbolo in self.alfabeto:
                        uniao = set()
                        for estado in conjunto:
                            uniao |= self.transicoes.get((estado, simbolo), set())

                        if uniao:
                            self.transicoes[(novo, simbolo)] = uniao

                    if conjunto & self.finais:
                        self.finais.add(novo)

                self.transicoes[chave] = {novos_estados[conjunto]}
                mudou = True

    def minimizar(self):
        conjunto_transicoes = {estado: set() for estado in self.estados}

        for (origem, simbolo), destinos in self.transicoes.items():
            if origem in conjunto_transicoes:
                conjunto_transicoes[origem] |= destinos

        mudou = True
        while mudou:
            mudou = False
            for estado in list(self.estados):
                novos = set()

                for alcancado in conjunto_transicoes[estado]:
                    if alcancado in conjunto_transicoes:
                        novos |= conjunto_transicoes[alcancado]

                tamanho_antigo = len(conjunto_transicoes[estado])
                conjunto_transicoes[estado] |= novos
                if len(conjunto_transicoes[estado]) > tamanho_antigo:
                    mudou = True

        inalcancaveis = set()
        for estado in self.estados:
            if estado == self.inicial:
                continue
            if estado not in conjunto_transicoes[self.inicial]:
                inalcancaveis.add(estado)

        mortos = set()
        for estado in self.estados:
            alcanca_final = False

            if estado in self.finais:
                alcanca_final = True
            else:
                for final in self.finais:
                    if final in conjunto_transicoes[estado]:
                        alcanca_final = True
                        break

            if not alcanca_final:
                mortos.add(estado)

        remover = mortos | inalcancaveis
        self.estados -= remover
        self.finais -= remover

        for chave in list(self.transicoes.keys()):
            origem, simbolo = chave
            destinos = self.transicoes[chave]

            if origem in remover or (destinos & remover):
                del self.transicoes[chave]

    def adicionar_estado_de_erro(self):
        # Estado de erro fixo "X": toda transição indefinida aponta para ele
        # e ele se auto-loopa em todos os símbolos do alfabeto.
        self.estados.add(self.erro)

        for estado in list(self.estados):
            for simbolo in self.alfabeto:
                if (estado, simbolo) not in self.transicoes:
                    self.transicoes[(estado, simbolo)] = {self.erro}

    # ------------------------------------------------------------------
    # Reconhecimento léxico (FITA + Tabela de Símbolos)
    # ------------------------------------------------------------------
    def _proximo_estado(self, estado, simbolo):
        # AF[EstadoCorrente, Símbolo]. Símbolo fora do alfabeto (ou sem
        # transição) leva ao estado de erro.
        destinos = self.transicoes.get((estado, simbolo))
        if not destinos:
            return self.erro
        return next(iter(destinos))  # AFD: só há um destino

    def _registrar_token(self, estado, rotulo, linha):
        # 6: se estado não final, EstadoCorrente = X
        if estado not in self.finais:
            estado = self.erro
        # 7: add FITA(EstadoCorrente)
        self.fita.append(estado)
        # 8: add TS(linha, EstadoCorrente, label)
        self.tabela_simbolos.append((linha, estado, rotulo))

    def reconhecer(self):
        # A entrada é a que já foi lida pelo autômato (self.entrada): cada
        # linha de token do arquivo, com o seu número de linha.
        self.fita = []
        self.tabela_simbolos = []

        for numero_linha, linha in self.entrada:
            estado_corrente = self.inicial  # 1: EstadoCorrente = S
            rotulo = ""                     # lexema sendo lido

            # O "\n" no final funciona como separador sentinela: garante que o
            # último token da linha seja fechado mesmo sem espaço depois dele.
            for simbolo in linha.rstrip("\r\n") + "\n":  # 2: Ler(Símbolo)
                if simbolo in self.SEPARADORES:          # 3: é separador -> vai para 6
                    if rotulo == "":
                        continue  # separadores repetidos, nada a registrar

                    self._registrar_token(estado_corrente, rotulo, numero_linha)  # 6, 7, 8

                    estado_corrente = self.inicial  # 9: volta para 1
                    rotulo = ""
                else:
                    # 4: EstadoCorrente = AF[EstadoCorrente, Símbolo]
                    estado_corrente = self._proximo_estado(estado_corrente, simbolo)
                    rotulo += simbolo
                    # 5: vai para 2 (próxima iteração)

        self.fita.append("$")

    # ------------------------------------------------------------------
    # Saídas
    # ------------------------------------------------------------------
    def imprimir_fita(self):
        print("FITA:", " ".join(self.fita))

    def imprimir_tabela_simbolos(self):
        print("Tabela de Símbolos:")
        print(f"{'LINHA':<8}{'IDENTIFICADOR':<16}RÓTULO")
        for linha, identificador, rotulo in self.tabela_simbolos:
            print(f"{linha:<8}{identificador:<16}{rotulo}")

    def salvar_saidas(self, arquivo_fita="fita.txt", arquivo_ts="tabela_simbolos.txt"):
        with open(arquivo_fita, "w", encoding="utf-8") as f:
            f.write(" ".join(self.fita) + "\n")

        with open(arquivo_ts, "w", encoding="utf-8") as f:
            f.write(f"{'LINHA':<8}{'IDENTIFICADOR':<16}RÓTULO\n")
            for linha, identificador, rotulo in self.tabela_simbolos:
                f.write(f"{linha:<8}{identificador:<16}{rotulo}\n")

    def _estados_ordenados(self):
        resto = sorted(self.estados - {self.inicial}, key=lambda e: (len(e), e))
        return [self.inicial] + resto

    def printar_automato(self):
        estados_ordenados = self._estados_ordenados()

        print("Palavras:", self.palavras)
        print("Alfabeto:", self.alfabeto)
        print("Estados:", estados_ordenados)
        print("Estado Inicial:", self.inicial)
        print("Estados Finais:", self.finais)
        print("Transições:", self.transicoes)
        for transicao, estado in self.transicoes.items():
            print(f"Transição: {transicao} -> Estado: {estado}")

        print("tabela de transições:")
        print("   ", end="")
        for letra in sorted(self.alfabeto):
            print(f"   {letra}", end="")
        print()

        for estado in estados_ordenados:
            if estado in self.finais:
                print(f" *{estado}", end="")
            else:
                print(f"{estado:>3}", end="")

            for letra in sorted(self.alfabeto):
                proximo_estado = self.transicoes.get((estado, letra), None)
                if proximo_estado is not None:
                    if isinstance(proximo_estado, set):
                        proximo_estado = "{" + ",".join(str(e) for e in sorted(proximo_estado)) + "}"
                    print(f" {proximo_estado:>3}", end="")
                else:
                    print("   -", end="")
            print()


if __name__ == "__main__":
    # uso: python analisador_lexico.py [tokens.txt]
    arquivo_tokens = sys.argv[1] if len(sys.argv) > 1 else "tokens.txt"

    automato = AutomatoeLexer()
    automato.carregar_palavras_e_gr(arquivo_tokens)
    automato.construir_automato_palavras()
    automato.construir_automato_gramatica_regular()
    automato.printar_automato()
    automato.determinizar()
    automato.printar_automato()
    automato.minimizar()
    automato.adicionar_estado_de_erro()
    automato.printar_automato()

    # reconhecimento léxico sobre a entrada já carregada
    automato.reconhecer()
    automato.imprimir_fita()
    automato.imprimir_tabela_simbolos()
    automato.salvar_saidas()