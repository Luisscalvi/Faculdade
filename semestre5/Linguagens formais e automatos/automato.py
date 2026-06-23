class Automato:

    def __init__(self):
        self.palavras = []
        self.alfabeto = set()
        self.estados = set()
        self.finais = set()
        self.transicoes = {}
        self.inicial = 0
        self.inalcancaveis = set()
        self.mortos = set()
        self._proximo_id = 1

    def carregar_palavras(self, nome_arquivo):
        with open(nome_arquivo, "r", encoding="utf-8") as arquivo:

            for linha in arquivo:

                palavra = linha.strip()

                if palavra == "":
                    continue

                self.palavras.append(palavra)

                for letra in palavra:
                    self.alfabeto.add(letra)

    def construir_automato(self):

        self.estados.add(self.inicial)  # adiciona o estado inicial aos estados

        for palavra in self.palavras:
            estado_atual = self.inicial  # começa no estado inicial

            for letra in palavra:
                proximo_estado = (estado_atual, letra)  # transição para o próximo estado pela letra

                if proximo_estado not in self.transicoes:  # cria um novo estado se a transição não existe
                    self.transicoes[proximo_estado] = self._proximo_id
                    self.estados.add(self._proximo_id)
                    self._proximo_id += 1

                estado_atual = self.transicoes[proximo_estado]  # vai para o próximo estado

            self.finais.add(estado_atual)  # adiciona estado atual aos estados finais

    def determinizar(self):
        novos_estados = {}
        prox_estado = max(self.estados) + 1

        mudou = True

        while mudou:

            mudou = False

            for chave in list(self.transicoes.keys()):

                destinos = self.transicoes[chave]

                if len(destinos) <= 1:
                    continue

                conjunto = frozenset(destinos)

                if conjunto not in novos_estados:

                    novo = prox_estado
                    prox_estado += 1

                    novos_estados[conjunto] = novo
                    self.estados.add(novo)

                    # calcular transições do novo estado
                    for simbolo in self.alfabeto:

                        uniao = set()

                        for estado in conjunto:
                            uniao |= self.transicoes.get(
                                (estado, simbolo),
                                set()
                            )

                        if uniao:
                            self.transicoes[(novo, simbolo)] = uniao

                    # estado final?
                    if conjunto & self.finais:
                        self.finais.add(novo)

                self.transicoes[chave] = {novos_estados[conjunto]}

                mudou = True
                
    def minimizar(self):
        # não lista indexada por inteiros contíguos
        conjunto_transicoes = {estado: set() for estado in self.estados}

        for (origem, simbolo), destino in self.transicoes.items():
            if origem in conjunto_transicoes:
                conjunto_transicoes[origem].add(destino)  # adiciona transições diretas

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
            destino = self.transicoes[chave]

            if origem in remover or destino in remover:
                del self.transicoes[chave]

    def adicionar_estado_de_erro(self):
        # Cria um estado de erro que representa transições indefinidas.
        estado_erro = max(self.estados) + 1 if self.estados else 1
        adicionou = False

        for estado in list(self.estados):
            for simbolo in self.alfabeto:
                if (estado, simbolo) not in self.transicoes:
                    # Qualquer transição ausente aponta para o estado de erro.
                    self.transicoes[(estado, simbolo)] = estado_erro
                    adicionou = True

        if adicionou:
            self.estados.add(estado_erro)
            for simbolo in self.alfabeto:
                # O estado de erro se auto-loopa em todos os símbolos.
                self.transicoes[(estado_erro, simbolo)] = estado_erro

    def printar_automato(self):
        print("Palavras:", self.palavras)
        print("Alfabeto:", self.alfabeto)
        print("Estados:", self.estados)
        print("Estado Inicial:", self.inicial)
        print("Estados Finais:", self.finais)
        print("Transições:", self.transicoes)
        for transicao, estado in self.transicoes.items():
            print(f"Transição: {transicao} -> Estado: {estado}")

        print("tabela de transições:")
        print("   ", end="")
        for letra in self.alfabeto:
            print(f"   {letra}", end="")
        print()

        for estado in self.estados:
            if estado in self.finais:
                print(f" *{estado}", end="")
            else:
                print(f"{estado:>3}", end="")

            for letra in self.alfabeto:
                proximo_estado = self.transicoes.get((estado, letra), None)
                if proximo_estado is not None:
                    if isinstance(proximo_estado, set):
                        proximo_estado = "{" + ",".join(str(e) for e in sorted(proximo_estado)) + "}"
                    print(f" {proximo_estado:>3}", end="")
                else:
                    print("   -", end="")
            print()


automato = Automato()
automato.carregar_palavras("tokens.txt")
automato.construir_automato()
automato.printar_automato()
automato.determinizar()
automato.minimizar()
automato.adicionar_estado_de_erro()
automato.printar_automato()