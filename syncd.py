#!/usr/bin/env python3

import requests
import watchdog
import logging
import time
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
import os
import yaml

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)


class GrafanaFileEventHandler(FileSystemEventHandler):

    def on_any_event(self, event):
        if event.is_directory:
            return
        process()


base_url = os.environ.get('GRAFANA_HOST', 'http://localhost:3000')
auth = (os.environ.get('GRAFANA_USER', 'admin'),
        os.environ.get('GRAFANA_PASS', 'admin'))

organizations = {}
users = {}
datasources = {}
dashboards = {}


def loadYAML(path):
    with open(path) as file:
        return yaml.load(file, Loader=yaml.FullLoader)


def writeYaml(org, name, deploy_dir, data):
    grafana_path = os.environ.get('GRAFANA_PROVISIONG_PATH', '../shared/')
    path = os.path.join(grafana_path, deploy_dir)
    if not os.path.isdir(path):
        os.makedirs(path)
    out_path = os.path.join(path, org+'-'+name+'.yaml')
    logging.info("Writing: " + out_path)
    with open(out_path, 'w') as out_file:
        out_data = {'apiVersion': 1}
        out_data.update(data)
        yaml.dump(out_data, out_file)


def process_file(file):
    if not file.endswith('yaml'):
        return
    logging.info("Prcessing: " + file)

    data = loadYAML(file)

    if 'users' in data:
        pass
    if 'organizations' in data:
        for org in data['organizations']:
            logging.info("Adding Org: " + org['name'])
            organizations[org['name']] = org

    if 'providers' in data:
        for provider in data['providers']:
            logging.info("Adding Provider: " + provider['name'])
            if 'orgName' not in provider:
                logging.info("providers require orgName")
                continue
            dashboards[provider['name']] = provider

    if 'datasources' in data:
        for datasource in data['datasources']:
            logging.info("Adding Datasource: " + datasource['name'])
            if 'orgName' not in datasource:
                logging.info("datasource require orgName")
                continue
            datasources[datasource['uid']] = datasource


def sync_orgs():
    logging.info("Syncing Orgs")
    for name, org in organizations.items():
        logging.info("Syncing Org: " + name)
        
        g_org = requests.get(base_url + '/api/orgs/name/' +
                             name, auth=auth).json()
        
        if g_org.get('message', "") == 'Organization not found':
            logging.info("Creating Org: " + name)
            g_org = requests.post(
                base_url + '/api/orgs', auth=auth, json=org).json()
        org.update(g_org)
    logging.info("Orgs synced.")


def sync_users():
    pass


def sync_datasources():
    logging.info("Provison Datasources")
    for uid, datasource in datasources.items():
        logging.info("Syncing Datasource: " + uid)
        orgName = datasource['orgName']
        g_org = requests.get(base_url + '/api/orgs/name/' +
                             orgName, auth=auth).json()
        if 'id' not in g_org:
            logging.info("Skipping: " + uid)
            continue
       
        ds = dict(datasource)
        ds['orgId'] = g_org['id']
        del ds['orgName']
        writeYaml(orgName, uid, 'datasources', {'datasources': [ds]})
        logging.info("Datasources provisioned.")


def sync_dashboards():
    pass


def triggerReload():
    requests.post(base_url + '/api/admin/provisioning/dashboards/reload',
                  auth=auth)
    requests.post(base_url + '/api/admin/provisioning/datasources/reload',
                  auth=auth)


def process():
    for subdir, dirs, files in os.walk(os.environ.get('INPUT_PROVISONING_PATH', '../test')):
        for file in files:
            process_file(os.path.join(subdir, file))
    done = False
    while not done:
        try:
            logging.info("Sync started")
            sync_orgs()
            sync_users()
            sync_datasources()
            sync_dashboards()
            logging.info("Synced")
            triggerReload()
            logging.info("Update triggered")
            done = True
        except Exception as e:
            logging.warning("Sync failed:" + str(e))
            time.sleep(1)


def main():
    event_handler = GrafanaFileEventHandler()
    observer = Observer()
    observer.schedule(event_handler, os.environ.get(
        'INPUT_PROVISONING_PATH', '../test'), recursive=True)
    process()

    observer.start()

    try:
        while True:
            time.sleep(1)
    finally:
        observer.stop()
        observer.join()


if __name__ == "__main__":
    main()

    #adminRoute.Post("/provisioning/dashboards/reload", Wrap(hs.AdminProvisioningReloadDashboards))
    #adminRoute.Post("/provisioning/plugins/reload", Wrap(hs.AdminProvisioningReloadPlugins))
    #adminRoute.Post("/provisioning/datasources/reload", Wrap(hs.AdminProvisioningReloadDatasources))
    #adminRoute.Post("/provisioning/notifications/reload", Wrap(hs.AdminProvisioningReloadNotifications))
