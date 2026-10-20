# GroundTruth v0.5 — Evidence packets (DEV, shadow-only)

**Important:** The excerpts are exact substrings of the saved retrieval report. They are candidate evidence, NOT answers, and no question has been adjudicated. A retrieved excerpt may be irrelevant or even contradict the assumption in the question.

Use the accompanying blind review CSV to record whether the combined evidence supports, contradicts, partially addresses, or does not establish each question.

## k8s-001

**Question:** What is a PersistentVolume in Kubernetes?

### E1 — stor-003-sec-002-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/storage/persistent-volumes/  
Heading: Persistent Volumes > Introduction  
Original saved excerpt offsets: [17, 331)  
Snippet cut or saved source already truncated: True

```text
Managing storage is a distinct problem from managing compute instances.
The PersistentVolume subsystem provides an API for users and administrators
that abstracts details of how storage is provided from how it is consumed.
To do this, we introduce two new API resources: PersistentVolume and PersistentVolumeClaim.
```

### E2 — stor-003-sec-002-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/storage/persistent-volumes/  
Heading: Persistent Volumes > Introduction  
Original saved excerpt offsets: [333, 555)  
Snippet cut or saved source already truncated: True

```text
A *PersistentVolume* (PV) is a piece of storage in the cluster that has been
provisioned by an administrator or dynamically provisioned using
[Storage Classes](https://kubernetes.io/docs/concepts/storage/storage-classes/).
```

### E3 — stor-002-sec-036-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/storage/volumes/  
Heading: Volumes > Types of volumes > persistentVolumeClaim  
Original saved excerpt offsets: [27, 335)  
Snippet cut or saved source already truncated: False

```text
A `persistentVolumeClaim` volume is used to mount a
[PersistentVolume](https://kubernetes.io/docs/concepts/storage/persistent-volumes/) into a Pod. PersistentVolumeClaims
are a way for users to "claim" durable storage (such as an iSCSI volume)
without knowing the details of the particular cloud environment.
```

### E4 — stor-003-sec-017-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/storage/persistent-volumes/  
Heading: Persistent Volumes > Lifecycle of a volume and claim > Reserving a PersistentVolume  
Original saved excerpt offsets: [34, 284)  
Snippet cut or saved source already truncated: True

```text
The control plane can [bind PersistentVolumeClaims to matching PersistentVolumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/#binding)
in the cluster. However, if you want a PVC to bind to a specific PV, you need to pre-bind them.
```

### E5 — stor-003-sec-017-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/storage/persistent-volumes/  
Heading: Persistent Volumes > Lifecycle of a volume and claim > Reserving a PersistentVolume  
Original saved excerpt offsets: [286, 574)  
Snippet cut or saved source already truncated: True

```text
By specifying a PersistentVolume in a PersistentVolumeClaim, you declare a binding
between that specific PV and PVC. If the PersistentVolume exists and has not reserved
PersistentVolumeClaims through its `claimRef` field, then the PersistentVolume and
PersistentVolumeClaim will be bound.
```

### E6 — stor-003-sec-026-ch-001 (retrieval rank 4)

Source: https://kubernetes.io/docs/concepts/storage/persistent-volumes/  
Heading: Persistent Volumes > Persistent Volumes  
Original saved excerpt offsets: [23, 281)  
Snippet cut or saved source already truncated: False

```text
Each PV contains a spec and status, which is the specification and status of the volume.
The name of a PersistentVolume object must be a valid
[DNS subdomain name](https://kubernetes.io/docs/concepts/overview/working-with-objects/names/#dns-subdomain-names).
```

---

## k8s-012

**Question:** Which Kubernetes VolumeSnapshot field automatically replicates snapshot data to every availability zone before a restore?

### E1 — stor-003-sec-068-ch-001 (retrieval rank 4)

Source: https://kubernetes.io/docs/concepts/storage/persistent-volumes/  
Heading: Persistent Volumes > Volume populators and data sources  
Original saved excerpt offsets: [39, 337)  
Snippet cut or saved source already truncated: False

```text
[Volume cloning](https://kubernetes.io/docs/concepts/storage/persistent-volumes/#volume-cloning) and
[snapshot restore](https://kubernetes.io/docs/concepts/storage/persistent-volumes/#volume-snapshot-and-restore-volume-from-snapshot-support) pre-populate
a new volume from a built-in *data source*.
```

### E2 — stor-008-sec-014-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/storage/volume-snapshots/  
Heading: Volume Snapshots > Provisioning Volumes from Snapshots  
Original saved excerpt offsets: [185, 380)  
Snippet cut or saved source already truncated: False

```text
For more details, see
[Volume Snapshot and Restore Volume from Snapshot](https://kubernetes.io/docs/concepts/storage/persistent-volumes/#volume-snapshot-and-restore-volume-from-snapshot-support).
```

### E3 — stor-008-sec-014-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/storage/volume-snapshots/  
Heading: Volume Snapshots > Provisioning Volumes from Snapshots  
Original saved excerpt offsets: [40, 183)  
Snippet cut or saved source already truncated: False

```text
You can provision a new volume, pre-populated with data from a snapshot, by using
the *dataSource* field in the `PersistentVolumeClaim` object.
```

### E4 — stor-008-sec-010-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/storage/volume-snapshots/  
Heading: Volume Snapshots > VolumeSnapshots  
Original saved excerpt offsets: [286, 448)  
Snippet cut or saved source already truncated: False

```text
`persistentVolumeClaimName` is the name of the PersistentVolumeClaim data source
for the snapshot. This field is required for dynamically provisioning a snapshot.
```

### E5 — stor-008-sec-002-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/storage/volume-snapshots/  
Heading: Volume Snapshots > Introduction  
Original saved excerpt offsets: [890, 1187)  
Snippet cut or saved source already truncated: True

```text
Volume snapshots provide Kubernetes users with a standardized way to copy a volume's
contents at a particular point in time without creating an entirely new volume. This
functionality enables, for example, database administrators to backup databases before
performing edit or delete modifications.
```

### E6 — stor-003-sec-068-ch-001 (retrieval rank 4)

Source: https://kubernetes.io/docs/concepts/storage/persistent-volumes/  
Heading: Persistent Volumes > Volume populators and data sources  
Original saved excerpt offsets: [338, 526)  
Snippet cut or saved source already truncated: False

```text
*Volume populators* extend this mechanism so that
a PersistentVolumeClaim can be pre-populated from other kinds of source (a custom resource),
referenced through its `dataSourceRef` field:
```

---

## k8s-018

**Question:** How can a NetworkPolicy select every namespace that was created after a particular date without adding any labels to those namespaces?

### E1 — net-006-sec-018-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/services-networking/network-policies/  
Heading: Network Policies > Targeting multiple namespaces by label  
Original saved excerpt offsets: [43, 217)  
Snippet cut or saved source already truncated: False

```text
In this scenario, your `Egress` NetworkPolicy targets more than one namespace using their
label names. For this to work, you need to label the target namespaces. For example:
```

### E2 — net-006-sec-018-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/services-networking/network-policies/  
Heading: Network Policies > Targeting multiple namespaces by label  
Original saved excerpt offsets: [335, 420)  
Snippet cut or saved source already truncated: False

```text
Add the labels under `namespaceSelector` in your NetworkPolicy document. For example:
```

### E3 — sched-003-sec-020-ch-001 (retrieval rank 4)

Source: https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/  
Heading: Assigning Pods to Nodes > Affinity and anti-affinity > Inter-pod affinity and anti-affinity > Namespace Selector  
Original saved excerpt offsets: [25, 447)  
Snippet cut or saved source already truncated: False

```text
You can also select matching namespaces using `namespaceSelector`, which is a label query over the set of namespaces.
The affinity term is applied to namespaces selected by both `namespaceSelector` and the `namespaces` field.
Note that an empty `namespaceSelector` ({}) matches all namespaces, while a null or empty `namespaces` list and
null `namespaceSelector` matches the namespace of the Pod where the rule is defined.
```

### E4 — sec-006-sec-018-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/security/rbac-good-practices/  
Heading: Role Based Access Control Good Practices > Kubernetes RBAC - privilege escalation risks > Namespace modification  
Original saved excerpt offsets: [356, 509)  
Snippet cut or saved source already truncated: False

```text
For clusters where NetworkPolicy is used, users may be set labels that indirectly allow
access to services that an administrator did not intend to allow.
```

### E5 — net-006-sec-020-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/services-networking/network-policies/  
Heading: Network Policies > Targeting a Namespace by its name  
Original saved excerpt offsets: [187, 335)  
Snippet cut or saved source already truncated: False

```text
While NetworkPolicy cannot target a namespace by its name with some object field, you can use the
standardized label to target a specific namespace.
```

### E6 — sec-006-sec-018-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/security/rbac-good-practices/  
Heading: Role Based Access Control Good Practices > Kubernetes RBAC - privilege escalation risks > Namespace modification  
Original saved excerpt offsets: [510, 783)  
Snippet cut or saved source already truncated: False

```text
For clusters using Dynamic Resource Allocation, labeling a namespace with
`resource.kubernetes.io/admin-access: "true"` allows any user who can create ResourceClaims in that namespace
to request admin access to devices already allocated to any other claim in any namespace.
```

---

## k8s-020

**Question:** How should replica counts be managed differently when a Deployment is controlled by a HorizontalPodAutoscaler versus when you manually scale a ReplicaSet?

### E1 — work-009-sec-032-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/workloads/controllers/deployment/  
Heading: Deployments > Writing a Deployment Spec > Replicas  
Original saved excerpt offsets: [114, 418)  
Snippet cut or saved source already truncated: False

```text
Should you manually scale a Deployment, example via `kubectl scale deployment deployment --replicas=X`, and then you update that Deployment based on a manifest
(for example: by running `kubectl apply -f deployment.yaml`),
then applying that manifest overwrites the manual scaling that you previously did.
```

### E2 — work-009-sec-032-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/workloads/controllers/deployment/  
Heading: Deployments > Writing a Deployment Spec > Replicas  
Original saved excerpt offsets: [420, 645)  
Snippet cut or saved source already truncated: False

```text
If a [HorizontalPodAutoscaler](https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/) (or any
similar API for horizontal scaling) is managing scaling for a Deployment, don't set `.spec.replicas`.
```

### E3 — work-011-sec-039-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/  
Heading: StatefulSets > PersistentVolumeClaim retention > Replicas  
Original saved excerpt offsets: [114, 415)  
Snippet cut or saved source already truncated: False

```text
Should you manually scale a StatefulSet, via `kubectl scale statefulset statefulset --replicas=X`, and then you update that StatefulSet
based on a manifest (for example: by running `kubectl apply -f statefulset.yaml`), then applying that manifest overwrites the manual scaling
that you previously did.
```

### E4 — work-011-sec-039-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/  
Heading: StatefulSets > PersistentVolumeClaim retention > Replicas  
Original saved excerpt offsets: [417, 817)  
Snippet cut or saved source already truncated: False

```text
If a [HorizontalPodAutoscaler](https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/)
(or any similar API for horizontal scaling) is managing scaling for a
Statefulset, don't set `.spec.replicas`. Instead, allow the Kubernetes
[control plane](https://kubernetes.io/docs/reference/glossary/?all=true#term-control-plane) to manage
the `.spec.replicas` field automatically.
```

### E5 — work-010-sec-020-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/workloads/controllers/replicaset/  
Heading: ReplicaSet > Working with ReplicaSets > ReplicaSet as a Horizontal Pod Autoscaler Target  
Original saved excerpt offsets: [54, 339)  
Snippet cut or saved source already truncated: False

```text
A ReplicaSet can also be a target for
[Horizontal Pod Autoscalers (HPA)](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/). That is,
a ReplicaSet can be auto-scaled by an HPA. Here is an example HPA targeting
the ReplicaSet we created in the previous example.
```

### E6 — work-010-sec-016-ch-001 (retrieval rank 4)

Source: https://kubernetes.io/docs/concepts/workloads/controllers/replicaset/  
Heading: ReplicaSet > Working with ReplicaSets > Scaling a ReplicaSet  
Original saved excerpt offsets: [424, 847)  
Snippet cut or saved source already truncated: False

```text
1. Pending (and unschedulable) pods are scaled down first
2. If controller.kubernetes.io/pod-deletion-cost annotation is set, then the pod with the lower value will come first.
3. Pods on nodes with more replicas come before pods on nodes with fewer replicas.
4. If the pods' creation times differ, the pod that was created more recently comes before the older pod (the creation times are bucketed on an integer log scale).
```

---

## k8s-024

**Question:** Which ResourceQuota field lets a namespace reserve a fixed percentage of total cluster CPU and automatically increases that namespace's quota whenever new nodes are added?

### E1 — sec-009-sec-017-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/policy/resource-quotas/  
Heading: Resource Quotas > Quota and Cluster Capacity  
Original saved excerpt offsets: [311, 569)  
Snippet cut or saved source already truncated: False

```text
- Proportionally divide total cluster resources among several teams.
- Allow each tenant to grow resource usage as needed, but have a generous limit to prevent accidental resource exhaustion.
- Detect demand from one namespace, add nodes, and increase quota.
```

### E2 — sec-009-sec-004-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/policy/resource-quotas/  
Heading: Resource Quotas > How Kubernetes ResourceQuotas work > Note:  
Original saved excerpt offsets: [914, 1098)  
Snippet cut or saved source already truncated: True

```text
If you enforce a resource quota in a namespace for either cpu or memory , you and other clients, must specify either requests or limits for that resource, for every new Pod you submit.
```

### E3 — sec-009-sec-017-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/policy/resource-quotas/  
Heading: Resource Quotas > Quota and Cluster Capacity  
Original saved excerpt offsets: [31, 251)  
Snippet cut or saved source already truncated: False

```text
ResourceQuotas are independent of the cluster capacity. They are
expressed in absolute units. So, if you add nodes to your cluster, this does *not*
automatically give each namespace the ability to consume more resources.
```

### E4 — sec-009-sec-004-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/policy/resource-quotas/  
Heading: Resource Quotas > How Kubernetes ResourceQuotas work > Note:  
Original saved excerpt offsets: [788, 913)  
Snippet cut or saved source already truncated: True

```text
- For cpu and memory resources, ResourceQuotas enforce that every (new) pod in that namespace sets a limit for that resource.
```

### E5 — conf-004-sec-040-ch-003 (retrieval rank 4)

Source: https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/  
Heading: Resource Management for Pods and Containers > Troubleshooting > My Pods are pending with event message `FailedScheduling`  
Original saved excerpt offsets: [1166, 1520)  
Snippet cut or saved source already truncated: True

```text
You can configure [resource quotas](https://kubernetes.io/docs/concepts/policy/resource-quotas/)
to limit the total amount of resources that a namespace can consume.
Kubernetes enforces quotas for objects in particular namespace when there is a
ResourceQuota in that namespace.
For example, if you assign specific namespaces to differ [TRUNCATED EXCERPT]
```

### E6 — sec-009-sec-004-ch-002 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/policy/resource-quotas/  
Heading: Resource Quotas > How Kubernetes ResourceQuotas work > Note:  
Original saved excerpt offsets: [0, 215)  
Snippet cut or saved source already truncated: False

```text
GiB and 10 cores, let B use 10GiB and 4 cores, and hold 2GiB and 2 cores in reserve for future allocation.
- Limit the "testing" namespace to using 1 core and 1GiB RAM. Let the "production" namespace use any amount.
```

---

## k8s-054

**Question:** Which PersistentVolumeClaim field tells Kubernetes to automatically convert an existing `Filesystem` PersistentVolume into raw `Block` mode when the requested `volumeMode` does not match?

### E1 — stor-003-sec-059-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/storage/persistent-volumes/  
Heading: Persistent Volumes > Raw Block Volume Support > PersistentVolumeClaim requesting a Raw Block Volume  
Original saved excerpt offsets: [0, 247)  
Snippet cut or saved source already truncated: False

````text
### PersistentVolumeClaim requesting a Raw Block Volume

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: block-pvc
spec:
  accessModes:
    - ReadWriteOnce
  volumeMode: Block
  resources:
    requests:
      storage: 10Gi
```
````

### E2 — stor-003-sec-029-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/storage/persistent-volumes/  
Heading: Persistent Volumes > Persistent Volumes > Volume Mode  
Original saved excerpt offsets: [873, 1066)  
Snippet cut or saved source already truncated: False

```text
See [Raw Block Volume Support](https://kubernetes.io/docs/concepts/storage/persistent-volumes/#raw-block-volume-support)
for an example on how to use a volume with `volumeMode: Block` in a Pod.
```

### E3 — stor-003-sec-029-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/storage/persistent-volumes/  
Heading: Persistent Volumes > Persistent Volumes > Volume Mode  
Original saved excerpt offsets: [459, 546)  
Snippet cut or saved source already truncated: False

```text
You can set the value of `volumeMode` to `Block` to use a volume as a raw block device.
```

### E4 — stor-002-sec-036-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/storage/volumes/  
Heading: Volumes > Types of volumes > persistentVolumeClaim  
Original saved excerpt offsets: [27, 335)  
Snippet cut or saved source already truncated: False

```text
A `persistentVolumeClaim` volume is used to mount a
[PersistentVolume](https://kubernetes.io/docs/concepts/storage/persistent-volumes/) into a Pod. PersistentVolumeClaims
are a way for users to "claim" durable storage (such as an iSCSI volume)
without knowing the details of the particular cloud environment.
```

### E5 — stor-003-sec-042-ch-001 (retrieval rank 4)

Source: https://kubernetes.io/docs/concepts/storage/persistent-volumes/  
Heading: Persistent Volumes > PersistentVolumeClaims  
Original saved excerpt offsets: [27, 290)  
Snippet cut or saved source already truncated: False

```text
Each PVC contains a spec and status, which is the specification and status of the claim.
The name of a PersistentVolumeClaim object must be a valid
[DNS subdomain name](https://kubernetes.io/docs/concepts/overview/working-with-objects/names/#dns-subdomain-names).
```

### E6 — stor-002-sec-036-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/storage/volumes/  
Heading: Volumes > Types of volumes > persistentVolumeClaim  
Original saved excerpt offsets: [337, 465)  
Snippet cut or saved source already truncated: False

```text
See the information about [PersistentVolumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/) for more
details.
```

---

## k8s-060

**Question:** Which Kubernetes setting retroactively injects Service environment variables into Pods that were already running before the Service was created?

### E1 — net-002-sec-043-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/services-networking/service/  
Heading: Service > Discovering services > Environment variables > Note:  
Original saved excerpt offsets: [12, 321)  
Snippet cut or saved source already truncated: False

```text
When you have a Pod that needs to access a Service, and you are using
the environment variable method to publish the port and cluster IP to the client
Pods, you must create the Service *before* the client Pods come into existence.
Otherwise, those client Pods won't have their environment variables populated.
```

### E2 — net-002-sec-042-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/services-networking/service/  
Heading: Service > Discovering services > Environment variables  
Original saved excerpt offsets: [27, 280)  
Snippet cut or saved source already truncated: False

```text
When a Pod is run on a Node, the kubelet adds a set of environment variables
for each active Service. It adds `{SVCNAME}_SERVICE_HOST` and `{SVCNAME}_SERVICE_PORT` variables,
where the Service name is upper-cased and dashes are converted to underscores.
```

### E3 — net-002-sec-042-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/services-networking/service/  
Heading: Service > Discovering services > Environment variables  
Original saved excerpt offsets: [282, 449)  
Snippet cut or saved source already truncated: False

```text
For example, the Service `redis-primary` which exposes TCP port 6379 and has been
allocated cluster IP address 10.0.0.11, produces the following environment
variables:
```

### E4 — conf-002-sec-012-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/configuration/configmap/  
Heading: ConfigMaps > Using ConfigMaps > Using Configmaps as environment variables  
Original saved excerpt offsets: [177, 461)  
Snippet cut or saved source already truncated: True

```text
1. For each container in your Pod specification, add an environment variable for each Configmap key that you want to use to the env[].valueFrom.configMapKeyRef field.
2. Modify your image and/or command line so that the program looks for values in the specified environment variables.
```

### E5 — conf-002-sec-012-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/configuration/configmap/  
Heading: ConfigMaps > Using ConfigMaps > Using Configmaps as environment variables  
Original saved excerpt offsets: [859, 940)  
Snippet cut or saved source already truncated: True

```text
The following Pod consumes the content of the ConfigMap as environment variables:
```

### E6 — work-002-sec-012-ch-001 (retrieval rank 4)

Source: https://kubernetes.io/docs/concepts/workloads/pods/  
Heading: Pods > Pod update and replacement  
Original saved excerpt offsets: [241, 629)  
Snippet cut or saved source already truncated: False

```text
Kubernetes doesn't prevent you from managing Pods directly. It is possible to
update some fields of a running Pod, in place. However, Pod update operations
like
[`patch`](https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.37/#patch-pod-v1-core), and
[`replace`](https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.37/#replace-pod-v1-core)
have some limitations:
```

---

## k8s-066

**Question:** Which ServiceAccount field automatically grants that account read access to every Secret in every namespace without creating any RBAC role or binding?

### E1 — sec-004-sec-003-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/security/service-accounts/  
Heading: Service Accounts > What are service accounts? > Default service accounts  
Original saved excerpt offsets: [167, 494)  
Snippet cut or saved source already truncated: False

```text
The `default`
service accounts in each namespace get no permissions by default other than the
[default API discovery permissions](https://kubernetes.io/docs/reference/access-authn-authz/rbac/#default-roles-and-role-bindings)
that Kubernetes grants to all authenticated principals if role-based access control (RBAC) is enabled.
```

### E2 — sec-004-sec-007-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/security/service-accounts/  
Heading: Service Accounts > How to use service accounts > Grant permissions to a ServiceAccount > Cross-namespace access using a ServiceAccount  
Original saved excerpt offsets: [432, 549)  
Snippet cut or saved source already truncated: False

```text
Then,
you'd create a RoleBinding object in the `maintenance` namespace to bind the
Role to the ServiceAccount object.
```

### E3 — sec-004-sec-006-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/security/service-accounts/  
Heading: Service Accounts > How to use service accounts > Grant permissions to a ServiceAccount  
Original saved excerpt offsets: [254, 344)  
Snippet cut or saved source already truncated: False

```text
You create a *role*, which grants access, and then *bind* the role to your
ServiceAccount.
```

### E4 — sec-004-sec-006-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/security/service-accounts/  
Heading: Service Accounts > How to use service accounts > Grant permissions to a ServiceAccount  
Original saved excerpt offsets: [43, 253)  
Snippet cut or saved source already truncated: False

```text
You can use the built-in Kubernetes
[role-based access control (RBAC)](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)
mechanism to grant the minimum permissions required by each service account.
```

### E5 — sec-004-sec-003-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/security/service-accounts/  
Heading: Service Accounts > What are service accounts? > Default service accounts  
Original saved excerpt offsets: [30, 166)  
Snippet cut or saved source already truncated: False

```text
When you create a cluster, Kubernetes automatically creates a ServiceAccount
object named `default` for every namespace in your cluster.
```

### E6 — sec-004-sec-007-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/security/service-accounts/  
Heading: Service Accounts > How to use service accounts > Grant permissions to a ServiceAccount > Cross-namespace access using a ServiceAccount  
Original saved excerpt offsets: [52, 184)  
Snippet cut or saved source already truncated: False

```text
You can use RBAC to allow service accounts in one namespace to perform actions
on resources in a different namespace in the cluster.
```

---

## k8s-073

**Question:** How does the API server's TLS server certificate protect an API connection differently from a Kubernetes client certificate issued through the CSR API?

### E1 — arch-003-sec-004-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/architecture/control-plane-node-communication/  
Heading: Communication between Nodes and the Control Plane > Control plane to node > API server to kubelet  
Original saved excerpt offsets: [233, 496)  
Snippet cut or saved source already truncated: False

```text
These connections terminate at the kubelet's HTTPS endpoint. By default, the API server does not
verify the kubelet's serving certificate, which makes the connection subject to man-in-the-middle
attacks and **unsafe** to run over untrusted and/or public networks.
```

### E2 — arch-003-sec-004-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/architecture/control-plane-node-communication/  
Heading: Communication between Nodes and the Control Plane > Control plane to node > API server to kubelet  
Original saved excerpt offsets: [498, 680)  
Snippet cut or saved source already truncated: False

```text
To verify this connection, use the `--kubelet-certificate-authority` flag to provide the API
server with a root certificate bundle to use to verify the kubelet's serving certificate.
```

### E3 — sec-006-sec-015-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/security/rbac-good-practices/  
Heading: Role Based Access Control Good Practices > Kubernetes RBAC - privilege escalation risks > CSRs and certificate issuing  
Original saved excerpt offsets: [34, 453)  
Snippet cut or saved source already truncated: False

```text
The CSR API allows for users with `create` rights to CSRs and `update` rights on `certificatesigningrequests/approval`
where the signer is `kubernetes.io/kube-apiserver-client` to create new client certificates
which allow users to authenticate to the cluster. Those client certificates can have arbitrary
names including duplicates of Kubernetes system components. This will effectively allow for privilege escalation.
```

### E4 — sec-005-sec-002-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/security/controlling-access/  
Heading: Controlling Access to the Kubernetes API > Transport security  
Original saved excerpt offsets: [330, 644)  
Snippet cut or saved source already truncated: False

```text
The API server presents a certificate. This certificate may be signed using
a private certificate authority (CA), or based on a public key infrastructure linked
to a generally recognized CA. The certificate and corresponding private key can be set
by using the `--tls-cert-file` and `--tls-private-key-file` flags.
```

### E5 — sec-005-sec-002-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/security/controlling-access/  
Heading: Controlling Access to the Kubernetes API > Transport security  
Original saved excerpt offsets: [646, 869)  
Snippet cut or saved source already truncated: False

```text
If your cluster uses a private certificate authority, you need a copy of that CA
certificate configured into your `~/.kube/config` on the client, so that you can
trust the connection and be confident it was not intercepted.
```

### E6 — conf-003-sec-019-ch-001 (retrieval rank 4)

Source: https://kubernetes.io/docs/concepts/configuration/secret/  
Heading: Secrets > Types of Secret > TLS Secrets  
Original saved excerpt offsets: [367, 593)  
Snippet cut or saved source already truncated: True

```text
When using this type of Secret, the `tls.key` and the `tls.crt` key must be provided
in the `data` (or `stringData`) field of the Secret configuration, although the API
server doesn't actually validate the values for each key.
```

---

## k8s-078

**Question:** How does resizing CPU or memory for a running container differ from resizing the `sizeLimit` of a memory-backed `emptyDir`, particularly in feature-gate requirements and what is being changed?

### E1 — conf-004-sec-023-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/  
Heading: Resource Management for Pods and Containers > How Kubernetes applies resource requests and limits > Considerations for memory backed `emptyDir` volumes > Note:  
Original saved excerpt offsets: [462, 714)  
Snippet cut or saved source already truncated: False

```text
When the `InPlacePodVerticalScalingMemoryBackedVolumes` feature gate is enabled, you can dynamically adjust the `sizeLimit` of a memory-backed (`medium: Memory`) `emptyDir` volume on a running Pod without requiring Pod recreation or container restarts.
```

### E2 — stor-002-sec-015-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/storage/volumes/  
Heading: Volumes > Types of volumes > emptyDir > emptyDir and in-place Pod resizing  
Original saved excerpt offsets: [491, 716)  
Snippet cut or saved source already truncated: False

```text
When the `InPlacePodVerticalScalingMemoryBackedVolumes` feature gate is enabled, you can dynamically adjust the `sizeLimit` of memory-backed (`medium: Memory`) `emptyDir` volumes, without restarting the Pod or its containers.
```

### E3 — work-003-sec-032-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/  
Heading: Pod Lifecycle > Resizing Pods > In-place Pod resize  
Original saved excerpt offsets: [1245, 1520)  
Snippet cut or saved source already truncated: True

```text
- Only CPU and memory resources can be resized in-place.
- The Pod's Quality of Service (QoS) class is determined at creation and cannot be changed by resizing.
- You can configure whether a container restart is required for the resize using resizePolicy  [TRUNCATED EXCERPT]
```

### E4 — conf-004-sec-023-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/  
Heading: Resource Management for Pods and Containers > How Kubernetes applies resource requests and limits > Considerations for memory backed `emptyDir` volumes > Note:  
Original saved excerpt offsets: [715, 933)  
Snippet cut or saved source already truncated: False

```text
For step-by-step instructions, see [Resize CPU and Memory Resources assigned to Containers](https://kubernetes.io/docs/tasks/configure-pod-container/resize-container-resources/#resizing-memory-backed-emptydir-volumes).
```

### E5 — stor-002-sec-015-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/storage/volumes/  
Heading: Volumes > Types of volumes > emptyDir > emptyDir and in-place Pod resizing  
Original saved excerpt offsets: [718, 923)  
Snippet cut or saved source already truncated: False

```text
For more details, see [Resize CPU and Memory Resources assigned to Containers](https://kubernetes.io/docs/tasks/configure-pod-container/resize-container-resources/#resizing-memory-backed-emptydir-volumes).
```

### E6 — work-003-sec-032-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/  
Heading: Pod Lifecycle > Resizing Pods > In-place Pod resize  
Original saved excerpt offsets: [25, 289)  
Snippet cut or saved source already truncated: True

```text
You can resize a Pod's container-level CPU and memory resources without recreating the Pod.
This is also called *in-place Pod vertical scaling*. This allows you to adjust resource
allocation for running containers while potentially avoiding application disruption.
```

---
