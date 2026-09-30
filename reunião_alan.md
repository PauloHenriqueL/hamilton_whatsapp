set. 30, 2026

## **Reunião em 30 de set. de 2026 às 14:26 GMT-03:00**

Registros da reunião [Transcrição](https://docs.google.com/document/d/1CJblcWAadg8K5Mi95R9yOwTw_6FItFVKYNf2y6tAKTQ/edit?usp=drive_web&tab=t.imr2lz76pee5) *(Algumas gravações estão indisponíveis)*

### **Resumo**

Reunião abordou simplificação de dados e automação via WhatsApp e painéis de controle.

**Simplificação e Automação de Prontuários**  
Foco na simplificação de dados e automação de prontuários via áudio no WhatsApp. Estabelecidos passos obrigatórios para a estrutura do prontuário.

**Diretrizes de Dados e Equipe**  
Debate sobre proteção de dados e LGPD com foco na omissão de nomes completos. Vitor assume exclusivamente a área comercial.

**Painel de Controle e IA Sofia**  
Apresentação do sistema de controle de terapeutas e discussão sobre a implementação futura da inteligência artificial Sofia.

### **Decisões**

## **Alinhada**

* **Prontuários via áudio no WhatsApp** A coleta de prontuários passará a ser realizada por meio de áudio transcrito via WhatsApp após as consultas.  
* **Estrutura obrigatória de quatro passos para prontuários** A mensagem de prontuário enviada via WhatsApp exigirá obrigatoriamente quatro etapas de preenchimento estruturado.  
* **Diretrizes sobre dados sensíveis nos prontuários** Um aviso explicativo será incluído para instruir os terapeutas a omitirem nomes completos e dados sensíveis.  
* **Cronograma do plantão vinculado à Sofia** A implementação do plantão foi postergada para um segundo momento, após a conclusão da inteligência artificial Sofia.

### **Próximas etapas**

- [ ] \[Artur\] Criar Mensagem Prontuário: Elaborar uma mensagem fixa para o WhatsApp contendo os 4 passos obrigatórios para o registro de prontuário dos terapeutas.  
- [ ] \[Artur\] Incluir Disclaimer: Incluir um aviso legal no sistema explicando a natureza do prontuário, a proibição de dados sensíveis e o uso do documento.  
- [ ] \[Artur\] Atualizar Painel: Adicionar o limite máximo de pacientes por terapeuta na tabela do painel de controle mestre.  
- [ ] \[Artur\] Ajustar Whisper: Remover ou ajustar a integração atual do whisper no fluxo de trabalho.  
- [ ] \[Artur\] Renomear Pacientes: Alterar a nomenclatura de paciente em destaque para paciente novo na interface de exibição.  
- [ ] \[Artur\] Consultar Vitor: Gravar ou enviar uma mensagem para Vitor questionando a necessidade de rastrear dados de pagamento e quantidade de consultas para verificar se podem ser removidos.

### **Detalhes**

* **Objetivos Principais e Simplificação de Dados**: Paulo Henrique Lima estabelece os objetivos centrais da operação, focando primeiramente na simplificação de dados e determinando que informações inúteis para a tomada de decisão não devem ser coletadas para evitar esforço e desgaste desnecessário ([00:00:01](#00:00:01)). Além disso, destaca a necessidade de menor fricção possível na coleta, priorizando o uso do WhatsApp e melhorias na visualização ([00:00:40](#00:00:40)). Outra premissa fundamental é a utilização exclusiva de dados confiáveis ("dados fortes"), exemplificando com a preferência por verificar extratos bancários em vez de perguntar se o pagamento foi realizado, estabelecendo que dados fortes nunca devem ser confrontados com dados fracos ([00:01:27](#00:01:27)).  
* **Automação de Prontuários e Escalonamento de Cobranças**: Paulo Henrique Lima discute a exigência do Conselho Regional de Psicologia de manter os prontuários dos últimos 5 anos ([00:02:09](#00:02:09)). Para otimizar o processo, sugere que as cobranças aos terapeutas ocorram apenas em casos de problemas, escalonando progressivamente via WhatsApp do terapeuta para o supervisor e, por fim, para Alan ([00:02:54](#00:02:54)). A desburocratização dos prontuários prevê o envio de uma mensagem automática no WhatsApp 1 hora e meia após a consulta, solicitando um áudio de 1 a 2 minutos com o relato da sessão, o qual será transcrito e salvo automaticamente no banco de dados ([00:03:30](#00:03:30)).  
* **Gerenciamento de Pacientes Novos e Painel Visual**: Discute-se o tratamento dado aos pacientes novos, que devem ser validados fora do processo seletivo e destacados adequadamente ([00:05:13](#00:05:13)) ([00:06:11](#00:06:11)). Paulo Henrique Lima aponta a necessidade de consolidar o número de pacientes ativos em um painel visual dedicado ao gestor da clínica ([00:05:53](#00:05:53)).  
* **Estrutura da Mensagem de WhatsApp e Etapas do Prontuário**: Artur testa a transcrição de áudio pelo WhatsApp e valida seu funcionamento ([00:06:55](#00:06:55)) ([00:09:09](#00:09:09)). Paulo Henrique Lima define os quatro passos obrigatórios que devem constar na mensagem estruturada e no áudio do prontuário: demanda e tema central da sessão, intervenções e procedimentos técnicos adotados, evolução e resposta do paciente, e encaminhamentos, intercorrências e próximos passos ([00:10:01](#00:10:01)). Artur assume a responsabilidade de enviar a mensagem pronta e fixa com esses quatro passos para o WhatsApp ([00:10:36](#00:10:36)).  
* **Diretrizes de Dados e Debates sobre Proteção de Dados**: Os participantes debatem os riscos relacionados à Lei Geral de Proteção de Dados e o uso de inteligência artificial externa com dados sensíveis de pacientes ([00:11:45](#00:11:45)) ([00:13:45](#00:13:45)). Paulo Henrique Lima argumenta que o vazamento do banco de dados principal representaria um risco muito maior do que o envio de dados via API, enquanto Alan e outros ponderam sobre os riscos de identificação pessoal e conformidade legal ([00:12:25](#00:12:25)) ([00:13:45](#00:13:45)). Conclui-se que, embora existam riscos teóricos e comparações com práticas comuns de mercado, a operação prossegue com os fluxos definidos ([00:13:12](#00:13:12)) ([00:14:34](#00:14:34)).  
* **Ajustes na Mensagem de Prontuário e Avisos de Dados Sensíveis**: Discute-se a necessidade de omitir nomes completos e dados íntimos nas mensagens para cumprir as normas do Conselho Regional de Psicologia ([00:15:54](#00:15:54)). Paulo Henrique Lima orienta que a mensagem enviada inclua uma explicação clara sobre o que é um prontuário, instruindo explicitamente a não inclusão de detalhes íntimos de pacientes ou segredos de terceiros ([00:16:28](#00:16:28)).  
* **Reestruturação de Equipe e Cronograma de Envio**: Aborda-se a mudança de função de Vitor, que passa a focar exclusivamente em vendas, comercial e processo seletivo, deixando a gestão da clínica ([00:18:07](#00:18:07)). Fica definido que a mensagem de WhatsApp para o prontuário será disparada meia hora após o horário agendado da consulta ([00:18:56](#00:18:56)).  
* **Painel de Controle e Gestão de Terapeutas**: Apresenta-se o sistema de controle onde o gestor visualiza os terapeutas, seus telefones, horários disponíveis informados no sistema Hamilton, número de pacientes ativos e limites combinados de pacientes ([00:21:04](#00:21:04)) ([00:21:32](#00:21:32)). Discute-se a aplicação de tags específicas (como palestras) que afetam a contagem de horas e a capacidade de atendimento, além da gestão de status entre ativos e inativos ([00:21:32](#00:21:32)) ([00:22:42](#00:22:42)).  
* **Organização de Plantão e Implementação da Inteligência Artificial Sofia**: Paulo Henrique Lima explica que a gestão de plantão será implementada em um segundo momento, após a estabilização das ferramentas ([00:25:19](#00:25:19)). Discute-se a utilização de uma inteligência artificial chamada Sofia no WhatsApp para realizar a triagem inicial e direcionar os atendimentos, avaliando-se a viabilidade técnica de números únicos versus números separados para diferentes áreas ([00:25:33](#00:25:33)).  
* **Avaliações de Juju e Próximos Passos do Projeto**: Paulo Henrique Lima menciona a função de Juju na condução de avaliações pós-consulta para fins de pesquisa, que futuramente será absorvida pela inteligência artificial Sofia ([00:27:08](#00:27:08)). Relatam-se entraves com Flávia em relação a permissões de repositório, e encerra-se com o direcionamento para criar protótipos, validá-los com Paulo Henrique Lima e consultar Vitor sobre o uso histórico dos dados de consultas e pagamentos ([00:27:49](#00:27:49)).

*Revise as anotações do Gemini para checar se estão corretas. [Confira dicas e saiba como o Gemini faz anotações](https://support.google.com/meet/answer/14754931)*

*Como está a qualidade de **destas observações?** [Responda a uma breve pesquisa](https://google.qualtrics.com/jfe/form/SV_5bXzKQfylMIhSXc?confid=I64m-zibR8Xo3fBSC2y9DxIOOBEQAjIGCIoCIAAYBQg&detailLevel=standard&hasImages=False&entryPoint=footerMain&isGoogler=False) para nos dar seu feedback, incluindo o quanto as observações foram úteis para o que você precisa.*

set. 30, 2026

## **Reunião em 30 de set. de 2026 às 14:26 GMT-03:00 \- Transcrição**

### **00:00:01** {#00:00:01}

**Paulo Henrique Lima:** Beleza? Ó, então, beleza. Então, vou falar de maneira organizada do primeiro. Aham. Quais são os nossos objetivos principais? Eu acho que são quatro. Enquanto eu vou falando, eu descubro o quinto. OK. Então, beleza. Primeiro objetivo é simplificação dos dados.

### **00:00:16**

**Paulo Henrique Lima:** Que que isso significa? Dado que não é útil para tomada de decisão, não deve ser coletado, OK? Porque coleta de dado é cap. Tá? Isso é esforço da pessoa, isso é tempo da pessoa, tipo assim, isso incomoda as pessoas, por mais que a maior parte assim, eh, isso é co.

### **00:00:40** {#00:00:40}

**Paulo Henrique Lima:** Então, primeira coisa é essa. Próximo. Isso é importante porque, e aí tô indo pro segundo tópico, assim, esse dado ele tem que ser coletado com o a menor fricção possível. Uhum. OK. Então, eh, se for possível jogar as coisas todas pro WhatsApp, eu prefiro que as coisas sejam jogadas pro WhatsApp.

### **00:00:58**

**Paulo Henrique Lima:** Tá? Se eh eu consigo melhorar a visualização da pessoa dos dados, eu quero melhorar a visualização da pessoa dos dados. Então, eh tudo com a menor fricção possível e com o maior grau de visualização possível assim. Eh, beleza? Então, além disso, que mais que a gente precisa assim, a gente precisa eh para as tomadas de decisões principais usarem eh dados que são de for, que que eu tô chamando de um dado de forte.

### **00:01:27** {#00:01:27}

**Paulo Henrique Lima:** Hã, é um dado que eu consigo colocar de maneira confiável. Eu tenho algum grau de segurança. Que esse dado ele é de verdade, não é um dado de mentira. Tipo estrato fantástico. Tipo estrato fantástico. Então entre perguntar pra pessoa se o paciente pagou ou ver no estrato se o paciente pagou, eu sempre vejo no estrato.

### **00:01:49**

**Paulo Henrique Lima:** Inclusive, uma premissa que é importante é eh não adianta confrontar um dado fraco com um dado forte. Uhum. Se eu tenho dado forte e um dado fraco, não tem por confrontar os dois. Eu realmente acredito no dado forte, tá? Essas são as premistas básicas. Eh, agora vamos para as consequências disso, tá?

### **00:02:09** {#00:02:09}

**Paulo Henrique Lima:** Então, beleza. Apresentei agora é mais a gente curtir, certo? O negócio que eu tô falando pro WhatsApp, OK? Eh, eu preciso de geração de prontuário pra pessoa, que o prontuário é uma requisição que o CRP faz pra gente, OK? que não é cobrada, né? Hum. Não é cobrada, mas pode ser, tá?

### **00:02:32**

**Paulo Henrique Lima:** Você tem que ter os prontuários dos últimos 5 anos, se o servido de entendeu? Uhum. Então, na prática não é cobrada, mas é bem provável que a aula seja servido, que é encher o nosso saco. OK? E aí eh tudo frância básica cara que encher o saco, eh o cara acha o detalhe ali da burocracia, você não tá cumprindo isso hamilon, né?

### **00:02:54** {#00:02:54}

**Paulo Henrique Lima:** É, esse é o que eu tá? Eh, então, qual que é a minha ideia? Eh, tudo que envolve cobrança pro terapeuta tem que acontecer só quando alguma coisa dá m\*\*\*\*. E de preferência eu gostaria que as pessoas não acessassem o remédito. Então, só acontecesse por WhatsApp. Então assim, eh, tem um paciente que não pagou, chega uma mensagem no WhatsApp do terapeuta, depois escala, chega no WhatsApp do supervisor, depois escala, chega no WhatsApp do Alan.

### **00:03:30** {#00:03:30}

**Paulo Henrique Lima:** Hum. OK. Eh, então a coisa vem escalando progressivamente, né, para tentar resolver as coisas no básico, assim, eh, mas isso tem que ser o mais burocratizado possível quando as coisas estão funcionando. Eh, aí, por exemplo, o que que eu tô chamando do mais desburocratizado quando as coisas estão funcionando? Hoje a pessoa escreve com texto o prontuário no Hamilton.

### **00:03:57**

**Paulo Henrique Lima:** Então ela tem que logar no Hamilton, ela tem que clicar lá, ela tem que cadastrar a sessão, ela tem que escrever o prontuário. É muito menos atrito se chegar uma mensagem de WhatsApp logo no momento depois da consulta, a consulta tá marcada para tal hora, né? Eh, 1 hora e meia depois da consulta, chegou uma mensagem assim numa mesma track, numa mesma conversa de WhatsApp, assim, olha, eh, a consulta do paciente tal foi realizada, fala que sim.

### **00:04:24**

**Paulo Henrique Lima:** E aí, eh, você pede para ela falar em um áudio de 1 minuto, 2 minutos, assim, como que foi a consulta? Esse áudio ele já é jogado para ele já é transcrito e aí a gente já salva isso no banco de dados como um prontuário, tá? Isso eu tenho que confirmar se pelo se a gente consegue acessar o áudio, transcrição de áudio no WhatsApp.

### **00:04:49**

**Paulo Henrique Lima:** Pelo WhatsApp se tivesse aqui, ser bom. Se ele tá dando uma palestra, se a gente não conseguir fazer isso, vou testar aqui agora por WhatsApp, o que que a gente vai fazer aí? A gente vai fazer isso por áudio no R, duas coisas. Eh, tem que lembrar tirar o whisper do lado já era dois já.

### **00:05:13** {#00:05:13}

**Paulo Henrique Lima:** Tá. Outra coisa, o paciente em um destaque não deveria entrar no processo seletivo. Eu o paciente faz de novo. Então a gente valida ele fora do processo seletivo para depois ser jogado no processo selutivo. Por exemplo, tô querendo criar um paciente em inglês, é precis italiano. Em inglês?

### **00:05:31**

**Paulo Henrique Lima:** Hum. Ah, stor, mas eu quero chegar na armé como opção inglês se vocês atenderem. brasileira que mora fora, mas preferem inglês. E aí você pode saber se você vai entender em inglês. Pode continuar. Não tá. Tô indo testar a questão do áudio. Tá.

### **00:05:53** {#00:05:53}

**Paulo Henrique Lima:** Mas você tá indo testar a questão do audio. Eh, então quais quais são os dados que eu te cito? Esse é o esse é o dado mais relevante de todos. Assim, eu preciso do número de pacientes que a pessoa tem ativo, eu tenho esse dado, correto? Esse dado então tem que tá num painel visual pro gestor da clínica.

### **00:06:11** {#00:06:11}

**Paulo Henrique Lima:** Pera, é, tem algum problema? Você pediu o sistema de vol para paciente. O mais voltado ia ser o paciente em destaque. Lembra disso? Ah, o paciente novo não ia ser o paciente em destaque. É, é isso mais não. Então coloca assim, ó. Eh, eu vou te dar um volt é uma é o que aparece o primeiro, mas o o primeiro de todos, o em destaque é o novo paciente.

### **00:06:34**

**Paulo Henrique Lima:** Melhor, né? Põe paciente novo em vez de paciente em destaque. Coloca um paciente com o paciente novo que é o mais que a gente precisa testar o mmr dele. O upv. Então coloca o seguinte, eh, tem um paciente em destaque, continua sendo um paciente novo, mas tem em ordem decrescente o mais votado.

### **00:06:55** {#00:06:55}

**Paulo Henrique Lima:** Isso. Como vai a família? Tô testando aqui. Eu não lembro de ter feito isso, mas parece que eu já fiz a questão do do áudio e às vezes dá problema, mas também eu tô com minha bunda, né? Se conseguir escrever escreveu a já fez os prontos.

### **00:07:34**

**Paulo Henrique Lima:** É, Artur. Hum. Manda o negócio de áudio que você fez para fato. Eu já mandei. Você fez era um box. Aham. Ela quer fazer tudo. Eu falei aqui que eu acho. Por que que não box? Porque fica mais fácil da pessoa visualizar o que ela tem que fazer.

### **00:07:53**

**Paulo Henrique Lima:** E eu acho estranho você pedir, tipo, muitas informações pro pessoal falar no áudio, só eu acho que sempre vai alguma coisa escapar, vai ficar muita fala, só que é a pésovar que terapeuta qualquer informação. Sim, se fosse uma conversa, um chat conversacional, mas eu não gosto de chat conversacional para outro ária. É, eu acho que sabe o que é mais fácil do que isso?

### **00:08:15**

**Paulo Henrique Lima:** Vai tá no WhatsApp, correto, Paulo? Teoria sim, a princípio sim. Tá, princípio sim. A mensagem que você manda já conta em pouquíssimas palavras a estrutura. Qual o seu áudio tem que conter? Tal coisa, tal fo tal coisa. Depois dando só mas vai faltar coisa e aí vai falar: "Ah, isso daqui não deixar no prontuário".

### **00:08:37**

**Paulo Henrique Lima:** Não, não, não tem coisas obrigatórias no pronto do CP, entende? E aí se se tá lá escrito obrigado quantas P seu cinco. Mas ela já mexeu no meu. Não sei como é que ele tá agora. Não, mas ela não subiu no seu. Ela tá subindo no meu.

### **00:09:09** {#00:09:09}

**Paulo Henrique Lima:** Seu tá igual. Acho que eu soltei ele. Não, sim. Ah, já tava para c\*\*\*\*\*\*. É, beleza. Onde já testei aqui, então em teoria sim. Teoria, eu mandei uns áudios aqui, ele ele transcreveu já. Vamos ver a família. Pronto, achei.

### **00:09:34**

**Paulo Henrique Lima:** Não funciona a princípio. Perfeito. Então, então só tem que montar essa primeira. Então, vamos fazer isso agora. Monta a primeira mensagem com as coisas que são necessárias. Não, não entendi. É porque isso aí eu não consigo dar uma instruction para isso aí, né?

### **00:09:48**

**Paulo Henrique Lima:** Que que você tá falando? Isso daí aí do WhatsApp. É isso aqui. Na verdade é a Sofia funcionando com uma IA rodando por trás e no sistema que eu criei. Ah, eu consigo colocar um I rodando por trás. Isso aí puxou. Tá, pode resolver, tá?

### **00:10:01** {#00:10:01}

**Paulo Henrique Lima:** Não sei também que você tá falando, mas tudo bem. É porque a não vai ser a Sofia, vai ser a que o Artur criou e aí ela vai pegar e criança rapidinho, ó. Então o que que é isso? Demanda e tema central da sessão. O segundo é não não não aqui não tá intervenções e procedimentos técnicos voltar intervenções.

### **00:10:36** {#00:10:36}

**Paulo Henrique Lima:** Procedimentos técnicos adotados. Uhum. Eh, evolução e resposta do paciente. Uhum. Encaminhamentos intercorrência própos passos. E isso daqui o cinco é putz. O cinco fiz não. Então, eh, faz o seguinte, Artur, me manda a mensagem do WhatsApp pronta, fixa, que tem esses quatro passos.

### **00:11:04**

**Paulo Henrique Lima:** Imagina o seguinte, a mensagem da vai receber falando que são os quatro passos obrigatórios de prontuário. Uhum. E aí o áudio dela tem conos quatro passos. OK. Pessoal que numa mensagem só botão de texto. Uhum. Ah, mas voltando aqui então só discutindo é que você quer simplificar os dados.

### **00:11:26**

**Paulo Henrique Lima:** O que te importa? Não te importa a quantidade de consultas que a pessoa fez. Hum. Que importa é se os pacientes estão pagando, número de pacientes que o terapeuta tem. Uhum. Fazer tudo por WhatsApp. É número de coisas que ele tá fazendo fora da clínica. Então, no painel de controle master, essa é uma informação que precisa.

### **00:11:45** {#00:11:45}

**Paulo Henrique Lima:** A gente não cai no problema do dados, não de LGBD, de usar IA externa para Ah, velho, já cancela LGBT. V fogo nesse documento também. Calma. É, por que que a gente cairia? Eu tô usando dado sensífico assim, dado pessoal. Não sei se dado pessoal, mas você não falou nome no pronto.

### **00:12:01**

**Paulo Henrique Lima:** Mas não é, é seu anonimizado. Isso falando da demanda que só aquela pessoa tem na vida. Esse é o problema. Põe fogo n ter fogo não fic doido. Sim. A pessoa tem depressão, você consegue não, mas isso se descrever como depressão, beleza. Agora você descrever, tem um problema específico com a tia que bate no primo por causa disso, daquilo.

### **00:12:25** {#00:12:25}

**Paulo Henrique Lima:** Um link disso, não precisa fazer o link. Se alguém process isso é real, você tá certo. Mas f\*\*\*-se na prática. Não, mas calma, calma, calma. Ó, a gente tem que ter o judicial. Como que uma empresa que a meta americana com essas informações tem acesso a Não, a questão não é se é empresa meta.

### **00:12:44**

**Paulo Henrique Lima:** Ess esses dados podem ser vazados e como a gente não é o detentor dos dados, o único detentor, a gente não pode se responsizar por outra pessoa vazar os dados. Dito isso, se os dados vazarem para todo mundo, é possível identificar quem é essa pessoa. Então, como que como que eles identifica em que é essa pessoa?

### **00:13:00**

**Paulo Henrique Lima:** Se eu sei que ele tem problema da vida dele. Não, eu sei que tá, mas os dados específicos são. Ele tem um problema e tem móvel matemática. Sim, mas aí você tem dado de váriasões. O nosso sistema já vai ter o nome do cara, velho. Então, tipo assim, já vai ter identificado o cara.

### **00:13:12** {#00:13:12}

**Paulo Henrique Lima:** Então, isso é irrelevante. Não, mas o que vai para Iá que vai para Iá é o nome do cara também, velho. Então, que eu tô falando, mas f\*\*\*-se aqui a questão eu acho que se alguém decidir processar disso alguns dias vai dar ruim, mas eu acho que ninguém vai. É, você tá saindo se fosse assim, maioria das coisas estão sendo feitas com IA não existe.

### **00:13:30**

**Paulo Henrique Lima:** Eu tava conversando com um tio da Amanda, que ele é tipo assim, ele trabalha com juiz juiz do trabalho lá e velho já existe um negócio chamado minuta Ia, vários juizes estão usando, tá ganhando uma p\*\*\* grana lá, tá totalmente não é para usar, já mil vezes que não é para usar, pessoal usando, tá ganhando uma grana, f\*\*\*-se.

### **00:13:45** {#00:13:45}

**Paulo Henrique Lima:** Não, calma, deixa eu só pensar. Eu tô falando que é um problema de GPB porque esses são dados são anonimizados. Não são nomizados. Eu sei o nome, cara. Eu sei. Não é só o áudio. Você consegue cruzar várias informações e construir quem é aquela pessoa, entendeu?

### **00:14:01**

**Paulo Henrique Lima:** Mas se vazar o banco dados do do Hamilton, que nem tá só na GBT do Hamilton, já acabou. Não. Sim, mas aí aí fodeu total. Mas isso aí não é não é o ponto. O ponto é eu posso mandar os dados específicos que que a IA vai usar pro para API. Tá, eu sei, mas eu acho que tipo assim, isso é o menor do nosso problema.

### **00:14:19**

**Paulo Henrique Lima:** O problema muito maior seria vazou o banco de dados da da do Hamilton, porque não é só dado para serizado, é o dado em si. Eu tenho o nome da fulana. Então assim, nós som correndo esse risco, tá correndo isso da meta. Não, a gente não tem risco de do Hamilton. Tem vai o quantos sites dado já caíram?

### **00:14:34** {#00:14:34}

**Paulo Henrique Lima:** Tipo assim, o Hamilton nunca caiu, graças a Deus. Mas tipo assim, então, mas os sites usavam eh WordPress e o problema que um plugin que tava, eu sei, mas existe, entendeu? Não tá OK. Então a cola é a seguinte, isso como produtos tales igual não dá isso. Uso interno dá porque todo mundo faz.

### **00:14:53**

**Paulo Henrique Lima:** Não, não dá, não dá, não dá, não dá, não dá. No CNPJ da m\*\*\*\*. da meta do multi for não r mas na dá na d para colocar as notas hipóteses isso aqui era um passo adicional que a gente tinha colocado para trabalhar a hipótese de casa não no WhatsApp do sistema do Hamilton é só só o só brotar com super que que deu recebi um alerta desse aqui que vai ter uma pancada de chuva fica esperto aí de moto bugado aí boa sorte lá vamos voltar aqui então.

### **00:15:29**

**Paulo Henrique Lima:** Hã, então seria um painel, né, um sistema onde a pessoa pelo WhatsApp, então no nosso tá, primeiro de tudo, no nosso sistema, alguém vai ter que ter esse controle de linkcar os pacientes com os terapeutas. Vai se atainar ainda pelo controle de pacientes. É para evitar falar, éão. É para evitar falar nome completo do paciente, dados pessoais ou eu não ponho?

### **00:15:54** {#00:15:54}

**Paulo Henrique Lima:** Então a Tainar, o fluxo seria Tainar link ao paciente. Não, calma, rapidinho, tá? Eh, calma, mas vai vir a Ah, a Não, f\*\*\*-se, f\*\*\*-se. f\*\*\*-se. f\*\*\*-se. Porque vai vir pra pessoa a mensagem do a sua consulta com o paciente tal, acabou de acontecer, como que foi a consulta?

### **00:16:08**

**Paulo Henrique Lima:** Aí a já vai ter acesso à porta do nome do paciente. Entendeu? É. Vai. Dá para pedir para omitir nome de outras pessoas. dados sensíveis. Eu acho que a prontuário do do CFP nem pode ter, né, dados sensíveis. Uhum. É melhor para sim.

### **00:16:28** {#00:16:28}

**Paulo Henrique Lima:** Tem muito no no na I, claro que pode. Tem que ser. Então, mas é porque o que é é sensível, acho que fica só pro psicólogo. É pronto, o cara pode pedir, né? É. Não. Então, faz um parágrafozinho explicando. Esse é um documento que pode ser isso vai fazer parte de um documento que pode ser acessado e é não deve constar detalhes íntimos do paciente, segredos de terceiros, compões, blá blá blá.

### **00:17:07**

**Paulo Henrique Lima:** Não. Ah, então isso aí de boa, pô. Isso aí, isso aí nem dado nem vai ter dado sensiv. Atacar e f\*\*\*-se. Sem disclaimer. Não, não, não. Põe esse disclaimer. Qual de não falar nome, dado sensível e tal, só que explica o que que é um prontuário pra pessoa.

### **00:17:25**

**Paulo Henrique Lima:** Tipo, uma mensagem explicando o que que é um prontuário, que que ela tem que fazer, entendeu? Só queário é uma mensagem. É para falar com a pessoa que não é sensível e coisa assim. Tá, foi mal, Paulo. Vamos. Não tinha estado. Pera aí.

### **00:18:07** {#00:18:07}

**Paulo Henrique Lima:** Ah, Você acha a gente tá sentindo isso? Saiu a gestão da eu ouvi na reunião geral, mas do nada é que aconteceu? Ah, o Vitor não tava fazendo direito mesmo. Ele quer ficar na parte de vendas. E agora o que vou cuidar dos dados das ele é ele assim.

### **00:18:25**

**Paulo Henrique Lima:** Aí precisa de alguém que vai fazer as coisas verdade agora o Víor vai ficar com comercial de empresa. Hã? O ficar comercial seletivo, Instagram e comercial. Uhum. Ah, sear. A clínica vai para quem? Vai dar tudo a clínica vai para quem? Ari ari tá não.

### **00:18:56** {#00:18:56}

**Paulo Henrique Lima:** Saium. Basicamente tudo que as pessoas tá fazendo na clínica mesmo o fá vagabundar É isso. aqui. Hum. Diz o que você tinha, só que não uma mensagem só, né? Uhum. Tá aí essa mensagem vai chegar pra pessoa meia hora depois do horário da consulta.

### **00:20:38**

**Paulo Henrique Lima:** Por que não no final da consulta? As pessoas demora mais com Mas se a mensagem chegar ela só ignora. Tá bom. Tá bom. Come aí paciente não ou texto, né? Audi test. Aí a vai sintetizar isso e fazer o documento isso. Tá.

### **00:21:04** {#00:21:04}

**Paulo Henrique Lima:** Então tá. A gente tá agora então o gestor da clínica, ele vai ter lá o controle de todos os pacientes e terapeutos, que é o que a Tainá faz hoje, o relacionamento que a Tainá faz hoje entre terapeuta e paciente e também vai ter outra tela que seria a tela de controle de terapeutas onde é a parte da tela de é horas de serviço, horas de Já tá aqui.

### **00:21:21**

**Paulo Henrique Lima:** Quer dar uma olhada? Hum. Não tem a questão da hora. Não sei se tem a questão da hora. Deixa eu ver. Tem as tag, né? Esse é o início. Esse é o início. Aí você tem aqui o albiris. O albiris.

### **00:21:32** {#00:21:32}

**Paulo Henrique Lima:** Aí você pode criar uma tag aqui que eu já criei uma tag que palestra. Você vem aqui e adiciona que o Alvíris é um cara muito bom de palestras. V adicionar aquele apto também. Aí você vai fazer, vai fazendo, vai fazendo. Horári. Aí a tec de cal que a pessoa tá fazendo.

### **00:21:47**

**Paulo Henrique Lima:** Aqui é o número de pacientes de verdade já. Isso. Isso. Passente tá cadastrada aqui no e aqui é o número do telefone dele. E aqui é o horário que ele disponibilizou. Ele entrou no sistema e colocou lá que tô disponível. Muitas pessoas não colocaram, tá?

### **00:21:58**

**Paulo Henrique Lima:** Uhum. É isso. Aí você pode filtrar, tá? Calma aí. Aqui tá atuar aqui o que a pessoa de fato tá fazendo. É que são os horários disponíveis. Sim. Que ela colocou no Rit. Uhum. Tá aí. Esses horários disponíveis tem aquilo que eu te falei que não sei se tava gravando já, que é eh é o número de pacientes aqui.

### **00:22:17**

**Paulo Henrique Lima:** Esses pacientes inclusive pode ser 6 barra não sei o quê, tá? Porque é o número de paciência que a pessoa está ativo e o número combinado. O número combinado eu vou imputar para todo mundo. Cada um vai ter um número diferente. Cada um vai ter um número diferente combinado.

### **00:22:30**

**Paulo Henrique Lima:** Tá. Achei que isso já não tinha não. Eu acho que o Vitor combinou com todo mundo. Deveria ter tal valor. É, é uma marca, tipo assim, a pessoa vai receber até 10\. Isso. Isso. Isso. Então isso isso tem que estar nessa tabela também.

### **00:22:42** {#00:22:42}

**Paulo Henrique Lima:** Você não acha que é melhor deixar até 10 pacientes? Porque tipo, se a pessoa perceber que, sei lá, Alan, não gosto de palestra, acho que eu queria realmente naquilo que eu já não, não tem 10 não, é porque cada pessoa um número diferente. É cada pessoa um número diferente. É, é Bernardo, onde Alice, não é?

### **00:22:59**

**Paulo Henrique Lima:** Hum, mas Alice, foca aqui, foca aqui, foca aqui, foca aqui. Vai lá, tá bom. Eh, cada pessoa combinou um número diferente. O seu é três, o do Víor Toscano é seis, o do Albires é seis, o do Mas agora da nova forma que o Víor tá fazendo, quer dizer, agora não, ao bom tempo que o Víor tá fazendo, é até 10 todos terapeutas.

### **00:23:27**

**Paulo Henrique Lima:** Não tá errado. F rev, então tem problema não. Beleza. Eh, até porque mexe de três em três, nem tem porque ser até 10\. Nem tem nem tem por ser até 10\. Depende das outras. Comicação agradável professor falar que são 10, mas você chegar realmente tá errado, a gente vai refazer.

### **00:23:46**

**Paulo Henrique Lima:** E aí se som adiciona palestra aqui, aí você vai combinar que palestra com com some duas horas dele e aí aqui eu já tenho informação ou não? Tá não, não. Aqui são os horários disponíveis aqui. Exato. É só quando então plantão, palestra, coisas que são pontuais, não comem os horários daqui, entendeu?

### **00:24:05**

**Paulo Henrique Lima:** Mas por exemplo, um grupo de estudos, aí ia ser legal se ele comesse o horário daqui, tá? Então vai ter que ter esse campo horário, só que no caso da palestra não tem horário aqui. Isso aí você marca que não tem. Isso, isso é o ideal. Eh, que mais aqui?

### **00:24:21**

**Paulo Henrique Lima:** Então, ó, tem o nome da pessoa, o telefone da pessoa, número de pacientes, número de pacientes máximo, tags, apto a e horário. Lembrando que algumas das apto a nunca mexe no horário, mas algumas das tags mexem no horário. Sim, tem o tem a questão de ativo inativo, porque alguns terapeutas nunca desativamos ninguém. Mentira, deveria desativar.

### **00:24:49**

**Paulo Henrique Lima:** Ah, não, eu não filtrei. Algumas pessoas estão ativas e inativas na aula. Deixa eu ver as pessoas aqui. Essas pessoas saíram, né? Não. Ok. Uhum. Não, isso aí pode manter que quando a pessoa sair da aula só mais fácil toca isso. Beleza, de boa.

### **00:25:05**

**Paulo Henrique Lima:** Tá. Aí a questão aqui era da da Tainá, não da é da Tainar. Ela vem aqui, ela vem. Talvez melhor até começar com a Tainar antes para ver o que que isso ajuda ela. Ela tem os terapeutas, pacientes e a Não, paraar não vai mudar nada porque ela só vai ter mais horários para marcar.

### **00:25:19** {#00:25:19}

**Paulo Henrique Lima:** Tá, entendeu? E aí, plantão a gente tem quando? Quando começar a ter Sofia, porque o problema principal hoje de plantão é a organização do bagulho, que a organização é feita pela Tainap. Então, o plantão vai ser o segundo momento. Resolve isso. Isso. Exato.

### **00:25:33** {#00:25:33}

**Paulo Henrique Lima:** Plantão é depois que a sua fita tiver implementada. Ah, isso é outra coisa. Vou ter que ver se dominamento porque no caso o WhatsApp que vai começar com nossos terapeutas é a Sofia também. Eu acho que é para separar é melhor. Então também acho, mas eu tenho que ver se tem como separar.

### **00:25:48**

**Paulo Henrique Lima:** vai direcionar para diferentes áreas, tipo se tiver alguém da formação, ela sabe que é para formação ou não. Esse é o dream de ter coisas diferentes. Testar, é, entendeu? Porque aí aí o que que dá para fazer? Dá para tudo chamar chega de tudo, dá para tudo chamar Sofia e ela direciona pras pessoas.

### **00:26:04**

**Paulo Henrique Lima:** É só que eu acho que a gente só pode cadastrar um número, então acho que vai, não sei um número para ela enviar. Não, não, bichão, um número só para ser a Sofia. Sofia, então é uma Sofia e ela manda o número das pessoas. Só que o ideal ia ser seria número diferente.

### **00:26:16**

**Paulo Henrique Lima:** Esse é o Dream que aí infinitamente nos Mas por três uma diferente cada uma diferente. Exato. Senão acho que a Sofia sozinha consegue fazer não. Então a só que aí o Víor fez a Sofia no monoprom que é o que eu falei se eu fosse fazer a Sofia fazer não faço ideia velho.

### **00:26:30**

**Paulo Henrique Lima:** De verdade eu tenho quase certeza que a Sofia não é um um orquestrador. Eu acho que é ela tava em reg ela tem as informações e de campos de ela ela como ela vai ter essa parte também a gente só muda ela. Alan, Alan, o Vitor nem pôs ela para rodar. É, tem que ver o que não pôs ainda.

### **00:26:50**

**Paulo Henrique Lima:** Tá lá ver isso aqui é uma coisa que você não pode largar, tem que terminar. Mas aí uma vez que a Sofia existe e que as coisas vão estão na mão da Tainá, aí Pode ter plantão, porque aí é o MIA que faz a triagem do plantão, tal, muito melhor, entendeu? Cata nem sempre solar na mão e tal, tá?

### **00:27:08** {#00:27:08}

**Paulo Henrique Lima:** Ah, tá. Lembrei que a questão que o Vitor fazia, se faz, que é Juju, questão de avaliação. Lembrei que é isso aqui agora. Hum. Eh, o ou Vitor ia fazer uma história dessa que depois você faz a primeira consulta, a Juju entra em contato com você, pergunta como foi a sua consulta e aí ela cadastra isso no Riton e aí só que isso é lico, a Juju não faz isso com todo mundo e isso é isso é lá, tipo assim, não é jogar fora.

### **00:27:34**

**Paulo Henrique Lima:** Então é uma função, uma vez que a Sofia que está entrando em contato, aí dá para coletar a data assim, tá? Mas falando assim, é uma função, é outra função que você poderia falar para Juju parar de fazer, que é uma coisa que ela faz. É, é uma função que é f\*\*\*-se. E porque tá me tá aqui no remetro, tá aqui para avaliar, não avaliar, tá aqui tudo.

### **00:27:49** {#00:27:49}

**Paulo Henrique Lima:** Então é aí hoje empurra essa m\*\*\*\* com a barriga, mas uma vez que a Sofia sair, isso é uma coisa que a Sofia deveria fazer. V que loucura. Isso é para o motivo professor Fu, porque eu tenho esses dados para fazer pesquisa, inclusive avaliação. Da Flávia não deixou ela clonar meu repositório que falou que ela não tinha os direitos reservados e pediu uma autorização escrita minha.

### **00:28:12**

**Paulo Henrique Lima:** Aí eu vou como colaborador aqui. Mas eu nunca vi isso acontecer aí. Louco, velho. Então vai ser só esse primeiro momento. Tá lá. Você tem aí é só pegar um avaliador, jogar em conção. Não é o interessador gerou nada. Pega o interessador e usou.

### **00:28:44**

**Paulo Henrique Lima:** No primeiro momento eu vou deixar só essas coisas que aí eu vou implementar e criar. Aí que que eu acho ideal? Eu faço um protótipo, a gente valida com você e aí a gente deixa o hamon rodando por enquanto. E aí você até conversa, aproveita esse tempo para conversar com o Víor e perguntar: "Víor, realmente para que você via comidade de consulta, por que você via com pagamento? Porque eu acho que ele usava isso para alguma coisa". Aí se realmente ele ele te falar e você acha que é inútil, a gente só tira, tá? Não, manda você gravar para ele. Hã? Manda você gravar sua para ele, tá? Quem quiser salvar alguma coisa é isso aí, senão só dorme Gomorra.

### **A transcrição foi encerrada após 00:29:15**

*Esta transcrição editável foi gerada por computador e pode conter erros. As pessoas também podem alterar o texto depois que ele for criado.*