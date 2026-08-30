# Runbook do Projeto — Monitoramento Geopolítico

Este documento detalha os procedimentos necessários para implantar, monitorar, reiniciar e ler logs do ecossistema de dados na VPS Linux.

## 1. Monitoramento e Observabilidade (Como ler os Logs)

O sistema registra logs contínuos em produção. Para inspecionar o comportamento do agendador e da ingestão sem abrir o ambiente de desenvolvimento, utilize o terminal Linux:


# Exibir os logs em tempo real (modo "follow") do agendador
tail -f /scheduler.log


---

## 2. Gerenciamento de Serviços com Systemd

O ingestor perene e o dashboard do Streamlit são gerenciados pelo gerenciador de processos nativo do Linux (`systemd`). Isso garante que eles iniciem sozinhos caso a VPS caia ou sofra reinicialização.

###  Verificar o Status dos Serviços

sudo systemctl status ingestor.service
sudo systemctl status streamlit.service


### Como Reiniciar os Componentes (Em caso de travamento)
Se houver instabilidade ou necessidade de forçar uma nova atualização imediata fora do horário agendado:

# Reiniciar o motor de ingestão (ele recarrega as tarefas)
sudo systemctl restart ingestor.service

# Reiniciar o Painel Streamlit
sudo systemctl restart streamlit.service


### Como Interromper os Serviços

sudo systemctl stop ingestor.service
sudo systemctl stop streamlit.service

---

## 3. Recuperação de Bloqueios de IP (Plano B do 5G/VPS)

Caso o log do agendador aponte falhas contínuas por bloqueio do YouTube (`IpBlocked`), o pipeline acionará automaticamente o fallback de dados sintéticos para que o dashboard continue online. 

Para forçar a renovação do endereço de IP e limpar o bloqueio:
1.  **Se rodando local pelo celular**: Ative o **Modo Avião** do smartphone por 10 segundos, desative e reinicie o serviço do ingestor.
2.  **Se rodando na VPS**: Acesse o painel da sua provedora de nuvem e execute um comando de "Reboot" no servidor para forçar o roteamento de um novo IP público pela interface de rede.
