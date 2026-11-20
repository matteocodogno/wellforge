import * as gcp from "@pulumi/gcp";

export const network = new gcp.compute.Network("shop", { autoCreateSubnetworks: false });
