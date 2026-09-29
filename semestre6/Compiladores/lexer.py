import string

class AutomatoeLexer:

    def __init__(self):
        self.palavras = []
        self.alfabeto = set()
        self.estados = set()
        self.finais = set()
        self.transicoes = {}  # mapa (estado origem, simbolo) -> set de estados destino
        self.inicial = "S"
        self.inalcancaveis = set()
        self.mortos = set()
        self.gramatica = {}
        self._gerador_nomes = self._criar_gerador_nomes()

    @staticmethod
    def _criar_gerador_nomes():
        # Gera nomes de estado como letras: A, B, C, ... Z, AA, BB, CC, ... ZZ, AAA, ...
        # sempre pulando a letra S, que é reservada para o estado inicial.
        tamanho = 1
        while True:
            for letra in string.ascii_uppercase:
                if letra == "S":
                    continue
                yield letra * tamanho
            tamanho += 1

    def _novo_estado(self):
        nome = next(self._gerador_nomes)
        self.estados.add(nome)
        return nome

    def carregar_palavras_e_gr(self, nome_arquivo):
        lendo_gramatica = False
        self.gramatica = {}

        with open(nome_arquivo, "r", encoding="utf-8") as arquivo:
            for linha in arquivo:
                linha = linha.strip()
                if linha == "":
                    lendo_gramatica = True
                    continue

                if not lendo_gramatica:
                    # palavras reservadas
                    self.palavras.append(linha)
                    for letra in linha:
                        self.alfabeto.add(letra)

                else:  # GR
                    esquerda, direita = linha.split("::=")
                    esquerda = esquerda.strip()
                    direita = direita.strip()

                    # remove os símbolos < > do não-terminal à esquerda, ex: "<S>" -> "S"
                    if esquerda.startswith("<") and esquerda.endswith(">"):
                        esquerda = esquerda[1:-1]

                    producoes = [] #sao armazenadas producoes no formato "a<Y>" ou "b<Z>" ou "ε"

                    for producao in direita.split("|"):
                        producao = producao.strip()
                        producoes.append(producao)

                        for c in producao:
                            if c.islower() and c != "ε":
                                self.alfabeto.add(c)

                    self.gramatica[esquerda] = producoes

    def construir_automato_palavras(self):
        # Constrói como uma trie; usa letras como nomes de estado e
        # guarda todo destino como set, mesmo quando há só um elemento.
        self.estados.add(self.inicial)

        for palavra in self.palavras:
            estado_atual = self.inicial  # começa no estado inicial

            for letra in palavra:
                chave = (estado_atual, letra)

                if chave not in self.transicoes:
                    # cria um novo estado se a transição não existe
                    novo = self._novo_estado()
                    self.transicoes[chave] = {novo}

                # vai para o(s) próximo(s) estado(s); como é trie, há só um
                estado_atual = next(iter(self.transicoes[chave]))

            self.finais.add(estado_atual)

    def construir_automato_gramatica_regular(self):
        if not self.gramatica:
            return

        # Mapeia cada não-terminal (ex: "S", "A") para o nome de estado real
        # do autômato. O não-terminal inicial "S" mapeia direto para o
        # próprio estado inicial; os demais recebem um novo nome do gerador
        # compartilhado, evitando colisão com os estados já usados pela trie.
        mapa_nao_terminal = {}
        for nao_terminal in self.gramatica:
            if nao_terminal == "S":
                mapa_nao_terminal[nao_terminal] = self.inicial
            else:
                mapa_nao_terminal[nao_terminal] = self._novo_estado()

        self.estados.add(self.inicial)

        # Processa cada produção: <X> ::= a<Y> | b<Z> | ... | ε
        for nao_terminal, producoes in self.gramatica.items():
            origem = mapa_nao_terminal[nao_terminal]

            for producao in producoes:
                if producao in ("ε", "", "epsilon"):
                    # produção vazia -> este estado é final
                    self.finais.add(origem)
                    continue

                # Convenção da gramática: um símbolo do alfabeto seguido,
                # opcionalmente, de um não-terminal entre <...>.
                if "<" in producao:
                    simbolo = producao[0]
                    nao_terminal_destino = producao[producao.index("<") + 1: producao.index(">")]
                    destino = mapa_nao_terminal[nao_terminal_destino]
                else:
                    # produção só com terminal, sem não-terminal: termina a cadeia
                    simbolo = producao
                    destino = self._novo_estado()
                    self.finais.add(destino)

                chave = (origem, simbolo)
                self.transicoes.setdefault(chave, set()).add(destino)

    def determinizar(self):
        novos_estados = {}
        prox_estado = self._novo_estado
        # algoritmo de determinização: enquanto houver estados com mais de um destino,
        # cria um novo estado para o conjunto de destinos
        mudou = True
        while mudou:
            mudou = False

            for chave in list(self.transicoes.keys()):
                destinos = self.transicoes[chave]
                if len(destinos) <= 1: #ignora estados ja determinizados
                    continue

                conjunto = frozenset(destinos)
                if conjunto not in novos_estados: #se o conjunto de destinos ainda não foi mapeado para um novo estado, cria um novo estado
                    novo = prox_estado()
                    novos_estados[conjunto] = novo # {C,K} = L

                    # calcular transições do novo estado
                    for simbolo in self.alfabeto:
                        uniao = set()
                        for estado in conjunto:
                            uniao |= self.transicoes.get((estado, simbolo), set())

                        if uniao: #se houver destinos para este símbolo, cria a transição do novo estado para o conjunto de destinos
                            self.transicoes[(novo, simbolo)] = uniao

                    # estado final?
                    if conjunto & self.finais:
                        self.finais.add(novo)

                self.transicoes[chave] = {novos_estados[conjunto]} # atualiza a transição para apontar para o novo estado determinizado
                mudou = True

    def minimizar(self):
        conjunto_transicoes = {estado: set() for estado in self.estados}

        for (origem, simbolo), destinos in self.transicoes.items():
            if origem in conjunto_transicoes:
                conjunto_transicoes[origem] |= destinos  # adiciona transições diretas

        mudou = True
        while mudou:  # adiciona as transicoes indiretas enquanto tiver mudanças
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

        # achar estados inalcançáveis
        inalcancaveis = set()
        for estado in self.estados:
            if estado == self.inicial:
                continue
            if estado not in conjunto_transicoes[self.inicial]:
                inalcancaveis.add(estado)

        # achar estados mortos
        mortos = set()
        for estado in self.estados:
            alcança_final = False

            if estado in self.finais:
                alcança_final = True
            else:
                for final in self.finais:
                    if final in conjunto_transicoes[estado]:
                        alcança_final = True
                        break

            if not alcança_final:
                mortos.add(estado)

        # remover estados mortos e inalcançáveis
        remover = mortos | inalcancaveis
        self.estados -= remover
        self.finais -= remover

        # remover estados mortos e inalcancaveis das transições
        for chave in list(self.transicoes.keys()):
            origem, simbolo = chave
            destinos = self.transicoes[chave]

            if origem in remover or (destinos & remover):
                del self.transicoes[chave]

    def adicionar_estado_de_erro(self):
        # Cria um estado de erro que representa transições indefinidas.
        adicionou = False
        estado_erro = None

        for estado in list(self.estados):
            for simbolo in self.alfabeto:
                if (estado, simbolo) not in self.transicoes:
                    if estado_erro is None:
                        estado_erro = self._novo_estado()
                    # Qualquer transição ausente aponta para o estado de erro.
                    self.transicoes[(estado, simbolo)] = {estado_erro}
                    adicionou = True

        if adicionou:
            for simbolo in self.alfabeto:
                # O estado de erro se auto-loopa em todos os símbolos.
                self.transicoes[(estado_erro, simbolo)] = {estado_erro}

    def _estados_ordenados(self):
        # Coloca o estado inicial primeiro, depois ordena o restante
        # alfabeticamente (considerando primeiro o tamanho do nome,
        # já que "AA" deve vir depois de "Z").
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




automato = AutomatoeLexer()
automato.carregar_palavras_e_gr("tokens.txt")
automato.construir_automato_palavras()
automato.construir_automato_gramatica_regular()
automato.printar_automato()
automato.determinizar()
automato.printar_automato()
automato.minimizar()
automato.adicionar_estado_de_erro()
automato.printar_automato()
