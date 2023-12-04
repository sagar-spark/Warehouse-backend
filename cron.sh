*/5 0-23 * * * /usr/bin/curl -H 'accessToken: system-delete-all-abrakadabra' https://apis.connectco.me/infra/delete-tokens/
*/10 0-23 * * * /usr/bin/curl -H 'accessToken: system-delete-all-abrakadabra' https://apis.connectco.me/infra/syncAllEmailsFromServer/
*/5 0-23 * * * /usr/bin/curl -H 'accessToken: system-delete-all-abrakadabra' https://apis.connectco.me/infra/cronUpdateAwbs/
*/5 0-23 * * * /usr/bin/curl -X POST -H 'accessToken: system-delete-all-abrakadabra' https://apis.connectco.me/infra/refreshTransactionForAllPendingBills/
