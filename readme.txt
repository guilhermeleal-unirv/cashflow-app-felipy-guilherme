==================================================
SISTEMA DE FLUXO DE CAIXA (CASHFLOW APP) - N2 & N3
==================================================

- Link Hospedagem: https://cashflow-app-xa03.onrender.com/
- Login: joao.paraiba
- Senha: costelaoNoDomingo
- LLM key: Informe sua Gemini API Key diretamente na interface web ou defina GEMINI_API_KEY no arquivo .env

**É esperado uma lentidão inicial pois está no render no modo gratuito e devido a inatividade é religado no primeiro acesso.

INSTRUÇÕES DE USO E PRINCIPAIS RECURSOS (N2):
1. Acesse o Link de Hospedagem acima e entre com o Usuário e Senha fornecidos.
2. Na Tela Principal (Lançar via IA), confira o "Código Última Atualização no GitHub" clicável no topo.
3. Para testar o lançamento inteligente: selecione o PDF de uma DANFE/NF-e e informe sua API Key Gemini.
4. Clique em "⚡ Analisar com IA": o sistema extrai dados e consulta Fornecedor, Faturado e Classificação.
5. Veja a análise prévia (indica se cada cadastro EXISTE, NÃO EXISTE ou se será reativado).
6. Clique em "✅ Confirmar lançamento": cadastra entidades ausentes e gera a Conta a Pagar com parcelas.
7. Menus Cadastros (Fornecedor/Cliente, Faturado, Classificação): tabelas abrem vazias por padrão.
8. Use a busca por múltiplos critérios ou clique em "TODOS" para listar apenas registros ATIVOS.
9. Clique nos títulos das colunas para alternar ordenação ascendente ou descendente.
10. Ações: Novo Cadastro, Editar e Exclusão Lógica (registros inativados ficam preservados).
11. Menus Movimentos (Contas a Pagar / Contas a Receber): lançamento com múltiplas parcelas e rateios.
12. Rodapé da barra lateral: exibe o usuário autenticado, botão Sair e atalho para o commit no GitHub.

==================================================
N3 - 3ª ETAPA: CONSULTA COM AGENTE INTELIGENTE (RAG)
==================================================
13. No menu lateral, clique em "🤖 Consulta RAG (N3)".
14. Digite uma pergunta em linguagem natural sobre o banco (ou clique em um dos exemplos rápidos).
    Exemplos de teste para prints:
    - RAG Simples: "Quais são as contas a pagar cadastradas e seus valores?"
    - RAG Embeddings: "Quanto gastamos com manutenção de trator ou peças agrícolas?"
15. Selecione o método de consulta:
    - "🔹 RAG Simples (SQL / Dados Estruturados) [25%]"
    - "🔸 RAG Embeddings (Busca Semântica Vetorial) [35%]"
    - "⚖️ Comparar Ambos (Lado a Lado)"
16. Clique em "🔍 Consultar com IA":
    - O sistema recupera os dados do banco (via SQL no Simples ou via Similaridade de Cosseno no Semântico).
    - Exibe a resposta elaborada gerada pelo Gemini baseada estritamente nos dados reais.
    - Exibe o painel de transparência com o Contexto / Fontes Recuperadas e score de similaridade.
17. Para a entrega da N3:
    - Print 1: Retorno da busca no modo RAG Simples.
    - Print 2: Retorno da busca no modo RAG Embeddings (Semântica).
