"""The bank systems the agents call, one module each (the design's section 20)."""

from . import crm, hub, my_contact, my_core, sg_as400, sg_cmm, sg_contact, sg_siebel, sg_soa

ROUTERS = [crm.router, hub.router, sg_as400.router, sg_soa.router, sg_siebel.router, sg_cmm.router, sg_contact.router, my_core.router, my_contact.router]
