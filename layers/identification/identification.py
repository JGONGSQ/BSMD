
from iroha import Iroha, IrohaCrypto
from iroha.primitive_pb2 import can_set_my_account_detail
from utils.iroha import IROHA_ADMIN, ADMIN_PRIVATE_KEY, send_transaction_and_print_status, NETWORK


class User:

    def __init__(self, private_key, public_key, name, domain):
        self.private_key = private_key
        self.public_key = public_key
        self.name = name
        self.domain = domain

    def create_user_in_iroha(self):
        """
        Create a personal account in a domain.
        :return: null:
        """
        # print(self.name, self.domain, self.public_key, self.private_key)
        tx = IROHA_ADMIN.transaction(
            [IROHA_ADMIN.command('CreateAccount',
                                 account_name=self.name,
                                 domain_id=self.domain,
                                 public_key=self.public_key)])
        IrohaCrypto.sign_transaction(tx, ADMIN_PRIVATE_KEY)
        send_transaction_and_print_status(tx)

    def get_balance(self):
        """
        Get the balance of my account
        :return: data: (array) asset id and assets quantity
        Return example:
        [asset_id: "fedcoin#federated"
        account_id: "generator@federated"
        balance: "1000"
        ]
        """
        account_id = self.name + '@' + self.domain
        iroha = Iroha(account_id)
        query = iroha.query('GetAccountAssets',
                            account_id=account_id)
        IrohaCrypto.sign_query(query, self.private_key)

        response = NETWORK.send_query(query)
        data = response.account_assets_response.account_assets
        for asset in data:
            print('Asset id = {}, balance = {}'.format(asset.asset_id, asset.balance))
        return data

    def set_detail(self, detail_key, detail_value):
        """
        Set a detail in my account. The details can be stored in JSON format with limit of 4096 characters per detail
        :param detail_key: (str) Name of the detail we want to set
        :param detail_value: (str) Value of the detail
        :return: null:
        Usage example:
        set_detail('age', '33')
        """
        print(self.name, self.domain, self.public_key, self.private_key, detail_key, detail_value)
        account_id = self.name + '@' + self.domain
        iroha = Iroha(account_id)
        tx = iroha.transaction([
            iroha.command('SetAccountDetail',
                          account_id=account_id,
                          key=detail_key,
                          value=detail_value)
        ])
        IrohaCrypto.sign_transaction(tx, self.private_key)
        send_transaction_and_print_status(tx)

    def get_all_details(self):
        """
        Consult all details of the node
        :return: data: (json) solicited details of the user
        Return example:
        {
            "nodeA@domain":{
                "Age":"35",
                "Name":"Quetzacoatl"
            },
            "nodeB@domain":{
                "Location":"35.3333535,-45.2141556464",
                "Status":"valid"
            },
            "nodeA@domainB":{
                "FederatingParam":"35.242553",
                "Loop":"3"
            }
        }
        """
        account_id = self.name + '@' + self.domain
        iroha = Iroha(account_id)
        query = iroha.query('GetAccountDetail',
                            account_id=account_id)
        IrohaCrypto.sign_query(query, self.private_key)
        response = NETWORK.send_query(query)
        data = response.account_detail_response
        print('Account id = {}, details = {}'.format(account_id, data.detail))
        return data.detail

    def get_all_details_from(self, user):
        """
        Consult all the details generated by some user. You must have the permission from the node
        to consult his information
        :param user: (obj) user you want details from
        :return: data: (json) solicited details of the user
        Usage example:
        get_detail_from_generator(Carlo)
        Return example:
        {
           "nodeA@domain":{
                "Age":"35",
                "Name":"Quetzacolatl"
            }
        }
        """
        account_id = self.name + '@' + self.domain
        generator_id = user.name + '@' + user.domain
        iroha = Iroha(account_id)
        query = iroha.query('GetAccountDetail',
                            account_id=account_id,
                            writer=generator_id)
        IrohaCrypto.sign_query(query, self.private_key)

        response = NETWORK.send_query(query)
        data = response.account_detail_response
        print('Account id = {}, details = {}'.format(account_id, data.detail))
        return data.detail

    def get_detail_from_generator(self, user, detail_id):
        """
        Consult a single detail generated by some user. You must have the permission from the node
        to consult his information
        :param user: (obj) user you want details from
        :param detail_id: (string) Name of the detail you want to consult
        :return: data: (json) solicited details of the user
        Usage example:
        get_detail_from_generator(Sara , 'Age')
        Return example:
        {
           "nodeA@domain":{
                 "Age":"35"
            }
        }
        """
        account_id = self.name + '@' + self.domain
        generator_id = user.name + '@' + user.domain
        iroha = Iroha(account_id)
        query = iroha.query('GetAccountDetail',
                            account_id=account_id,
                            writer=generator_id,
                            key=detail_id)
        IrohaCrypto.sign_query(query, self.private_key)

        response = NETWORK.send_query(query)
        data = response.account_detail_response
        print('Account id = {}, details = {}'.format(account_id, data.detail))
        return data.detail

    def set_detail_to(self, user, detail_key, detail_value):
        """
        Set the details of a node. The details can be stored in JSON format with limit of 4096 characters per detail.
        You must have the permission from the node to set information on his identification
        :param user: (obj) user you want to set the details
        :param detail_key: (str) Name of the detail we want to set
        :param detail_value: (str) Value of the detail
        :return: null:
        Usage example:
        set_detail(Lucas, 'key', 'age', '33')
        """
        account = self.name + '@' + self.domain
        iroha = Iroha(account)
        account_id = user.name + '@' + user.domain
        tx = iroha.transaction([
            iroha.command('SetAccountDetail',
                          account_id=account_id,
                          key=detail_key,
                          value=detail_value)
        ])
        IrohaCrypto.sign_transaction(tx, self.private_key)
        send_transaction_and_print_status(tx)

    def grants_access_set_details_to(self, user):
        """
        Grant permission to a node to set details on your identification
        :param user: (obj) user you want to grant permissions to set detail on your behalf
        :return:
        """
        my_id_account = self.name + '@' + self.domain
        grant_account_id = user.name + '@' + user.domain
        iroha = Iroha(my_id_account)
        tx = iroha.transaction([
            iroha.command('GrantPermission',
                          account_id=grant_account_id,
                          permission=can_set_my_account_detail)
        ],
            creator_account=my_id_account)
        IrohaCrypto.sign_transaction(tx, self.private_key)
        send_transaction_and_print_status(tx)

    def transfer_assets_to(self, user, asset_name, quantity, description):
        """
        Transfer assets from one account to another. Both users must be in the same domain
        :param user: (obj) user you want to transfer the assets
        :param asset_name: (str) name of the asset to be transferred
        :param quantity: (float) Number of assets we want to transfer
        :param description: (str) Small message to the receiver of assets
        :return:
        Example:
        transfer_assets(Dante, 'coin', '2', 'Shut up and take my money')
        """

        account_id = self.name + '@' + self.domain
        iroha = Iroha(account_id)
        destination_account = user.name + '@' + self.domain
        asset_id = asset_name + '#' + self.domain
        tx = iroha.transaction([
            iroha.command('TransferAsset',
                          src_account_id=account_id,
                          dest_account_id=destination_account,
                          asset_id=asset_id,
                          description=description,
                          amount=quantity)
        ])
        IrohaCrypto.sign_transaction(tx, self.private_key)
        send_transaction_and_print_status(tx)