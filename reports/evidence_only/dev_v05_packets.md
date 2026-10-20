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

## k8s-002

**Question:** How does Kubernetes expose a Service outside the cluster?

### E1 — net-002-sec-018-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/services-networking/service/  
Heading: Service > Service type  
Original saved excerpt offsets: [17, 190)  
Snippet cut or saved source already truncated: True

```text
For some parts of your application (for example, frontends) you may want to expose a
Service onto an external IP address, one that's accessible from outside of your
cluster.
```

### E2 — net-002-sec-018-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/services-networking/service/  
Heading: Service > Service type  
Original saved excerpt offsets: [638, 822)  
Snippet cut or saved source already truncated: True

```text
You can expose the Service to the public internet using an
[Ingress](https://kubernetes.io/docs/concepts/services-networking/ingress/) or a
[Gateway](https://gateway-api.sigs.k8s.io/).
```

### E3 — net-002-sec-002-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/services-networking/service/  
Heading: Service > Services in Kubernetes  
Original saved excerpt offsets: [27, 282)  
Snippet cut or saved source already truncated: True

```text
The Service API, part of Kubernetes, is an abstraction to help you expose groups of
Pods over a network. Each Service object defines a logical set of endpoints (usually
these endpoints are Pods) along with a policy about how to make those pods accessible.
```

### E4 — net-001-sec-002-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/services-networking/  
Heading: Services, Load Balancing, and Networking > The Kubernetes network model  
Original saved excerpt offsets: [845, 1291)  
Snippet cut or saved source already truncated: True

```text
On Windows, this rule does not apply to host-network pods.
  - Agents on a node (such as system daemons, or kubelet) can communicate with all pods on that node.
- The [Service](https://kubernetes.io/docs/concepts/services-networking/service/) API lets you provide a stable (long lived) IP address or hostname for a service implemented by one or more backend pods, where the individual pods making up the service can change over time.
- Kubernetes
```

### E5 — net-001-sec-002-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/services-networking/  
Heading: Services, Load Balancing, and Networking > The Kubernetes network model  
Original saved excerpt offsets: [1292, 1520)  
Snippet cut or saved source already truncated: True

```text
automatically manages [EndpointSlice](https://kubernetes.io/docs/concepts/services-networking/endpoint-slices/) objects to provide information about the pods currently backing a Service.
  - A service proxy i [TRUNCATED EXCERPT]
```

### E6 — net-002-sec-002-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/services-networking/service/  
Heading: Service > Services in Kubernetes  
Original saved excerpt offsets: [643, 691)  
Snippet cut or saved source already truncated: True

```text
The Service abstraction enables this decoupling.
```

---

## k8s-003

**Question:** What is a persistentVolumeClaim volume used for?

### E1 — stor-002-sec-036-ch-001 (retrieval rank 1)

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

### E2 — stor-003-sec-065-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/storage/persistent-volumes/  
Heading: Persistent Volumes > Volume Snapshot and Restore Volume from Snapshot Support > Create a PersistentVolumeClaim from a Volume Snapshot  
Original saved excerpt offsets: [0, 372)  
Snippet cut or saved source already truncated: False

````text
### Create a PersistentVolumeClaim from a Volume Snapshot

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: restore-pvc
spec:
  storageClassName: csi-hostpath-sc
  dataSource:
    name: new-snapshot-test
    kind: VolumeSnapshot
    apiGroup: snapshot.storage.k8s.io
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
```
````

### E3 — stor-003-sec-067-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/storage/persistent-volumes/  
Heading: Persistent Volumes > Volume Cloning > Create PersistentVolumeClaim from an existing PVC  
Original saved excerpt offsets: [0, 338)  
Snippet cut or saved source already truncated: False

````text
### Create PersistentVolumeClaim from an existing PVC

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: cloned-pvc
spec:
  storageClassName: my-csi-plugin
  dataSource:
    name: existing-src-pvc-name
    kind: PersistentVolumeClaim
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
```
````

### E4 — stor-003-sec-002-ch-001 (retrieval rank 4)

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

### E5 — stor-003-sec-002-ch-001 (retrieval rank 4)

Source: https://kubernetes.io/docs/concepts/storage/persistent-volumes/  
Heading: Persistent Volumes > Introduction  
Original saved excerpt offsets: [879, 946)  
Snippet cut or saved source already truncated: True

```text
A *PersistentVolumeClaim* (PVC) is a request for storage by a user.
```

### E6 — stor-002-sec-036-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/storage/volumes/  
Heading: Volumes > Types of volumes > persistentVolumeClaim  
Original saved excerpt offsets: [337, 465)  
Snippet cut or saved source already truncated: False

```text
See the information about [PersistentVolumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/) for more
details.
```

---

## k8s-005

**Question:** How can external IPs be used with Kubernetes Services?

### E1 — net-002-sec-049-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/services-networking/service/  
Heading: Service > External IPs  
Original saved excerpt offsets: [169, 542)  
Snippet cut or saved source already truncated: False

```text
If there are external IPs that route to one or more cluster nodes, Kubernetes Services
can be exposed on those `externalIPs`. When network traffic arrives into the cluster, with
the external IP (as destination IP) and the port matching that Service, rules and routes
that Kubernetes has configured ensure that the traffic is routed to one of the endpoints
for that Service.
```

### E2 — net-002-sec-049-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/services-networking/service/  
Heading: Service > External IPs  
Original saved excerpt offsets: [544, 907)  
Snippet cut or saved source already truncated: False

```text
When you define a Service, you can specify `externalIPs` for any
[service type](https://kubernetes.io/docs/concepts/services-networking/service/#publishing-services-service-types).
In the example below, the Service named `"my-service"` can be accessed by clients using TCP,
on `"198.51.100.32:80"` (calculated from `.spec.externalIPs[]` and `.spec.ports[].port`).
```

### E3 — net-002-sec-009-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/services-networking/service/  
Heading: Service > Defining a Service > Services without selectors > Note:  
Original saved excerpt offsets: [174, 401)  
Snippet cut or saved source already truncated: False

```text
The endpoint IP addresses cannot be the cluster IPs of other Kubernetes Services,
because [kube-proxy](https://kubernetes.io/docs/reference/command-line-tools-reference/kube-proxy/) doesn't support virtual IPs
as a destination.
```

### E4 — net-002-sec-018-ch-001 (retrieval rank 4)

Source: https://kubernetes.io/docs/concepts/services-networking/service/  
Heading: Service > Service type  
Original saved excerpt offsets: [1134, 1299)  
Snippet cut or saved source already truncated: True

```text
**[`LoadBalancer`](https://kubernetes.io/docs/concepts/services-networking/service/#loadbalancer)**
: Exposes the Service externally using an external load balancer.
```

### E5 — net-002-sec-009-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/services-networking/service/  
Heading: Service > Defining a Service > Services without selectors > Note:  
Original saved excerpt offsets: [12, 172)  
Snippet cut or saved source already truncated: False

```text
The endpoint IPs *must not* be: loopback (127.0.0.0/8 for IPv4, ::1/128 for IPv6), or
link-local (169.254.0.0/16 and 224.0.0.0/24 for IPv4, fe80::/64 for IPv6).
```

### E6 — net-002-sec-018-ch-001 (retrieval rank 4)

Source: https://kubernetes.io/docs/concepts/services-networking/service/  
Heading: Service > Service type  
Original saved excerpt offsets: [17, 190)  
Snippet cut or saved source already truncated: True

```text
For some parts of your application (for example, frontends) you may want to expose a
Service onto an external IP address, one that's accessible from outside of your
cluster.
```

---

## k8s-007

**Question:** What is the role of the Kubernetes cloud-controller-manager?

### E1 — arch-007-sec-001-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/architecture/cloud-controller/  
Heading: Cloud Controller Manager  
Original saved excerpt offsets: [228, 630)  
Snippet cut or saved source already truncated: False

```text
The cloud-controller-manager is a Kubernetes [control plane](https://kubernetes.io/docs/reference/glossary/?all=true#term-control-plane) component
that embeds cloud-specific control logic. The cloud controller manager lets you link your
cluster into your cloud provider's API, and separates out the components that interact
with that cloud platform from components that only interact with your cluster.
```

### E2 — arch-007-sec-001-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/architecture/cloud-controller/  
Heading: Cloud Controller Manager  
Original saved excerpt offsets: [632, 876)  
Snippet cut or saved source already truncated: False

```text
By decoupling the interoperability logic between Kubernetes and the underlying cloud
infrastructure, the cloud-controller-manager component enables cloud providers to release
features at a different pace compared to the main Kubernetes project.
```

### E3 — arch-007-sec-013-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/architecture/cloud-controller/  
Heading: Cloud Controller Manager > What's next  
Original saved excerpt offsets: [16, 465)  
Snippet cut or saved source already truncated: True

```text
- [Cloud Controller Manager Administration](https://kubernetes.io/docs/tasks/administer-cluster/running-cloud-controller/#cloud-controller-manager) has instructions on running and managing the cloud controller manager.
- To upgrade a HA control plane to use the cloud controller manager, see [Migrate Replicated Control Plane To Use Cloud Controller Manager](https://kubernetes.io/docs/tasks/administer-cluster/controller-manager-leader-migration/).
```

### E4 — arch-007-sec-013-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/architecture/cloud-controller/  
Heading: Cloud Controller Manager > What's next  
Original saved excerpt offsets: [466, 912)  
Snippet cut or saved source already truncated: True

```text
- Want to know how to implement your own cloud controller manager, or extend an existing project?
- The cloud controller manager uses Go interfaces, specifically, CloudProvider interface defined in `cloud.go` from kubernetes/cloud-provider to allow implementations from any cloud to be plugged in.
  - The implementation of the shared controllers highlighted in this document (Node, Route, and Service), and some scaffolding along with the shared
```

### E5 — arch-007-sec-002-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/architecture/cloud-controller/  
Heading: Cloud Controller Manager > Design  
Original saved excerpt offsets: [43, 318)  
Snippet cut or saved source already truncated: False

```text
The cloud controller manager runs in the control plane as a replicated set of processes
(usually, these are containers in Pods). Each cloud-controller-manager implements
multiple [controllers](https://kubernetes.io/docs/concepts/architecture/controller/) in a single
process.
```

### E6 — arch-007-sec-006-ch-001 (retrieval rank 4)

Source: https://kubernetes.io/docs/concepts/architecture/cloud-controller/  
Heading: Cloud Controller Manager > Cloud controller manager functions > Route controller  
Original saved excerpt offsets: [22, 205)  
Snippet cut or saved source already truncated: False

```text
The route controller is responsible for configuring routes in the cloud
appropriately so that containers on different nodes in your Kubernetes
cluster can communicate with each other.
```

---

## k8s-008

**Question:** How are Kubernetes compute resource types such as CPU and memory different from API resources such as Pods and Services?

### E1 — conf-004-sec-004-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/  
Heading: Resource Management for Pods and Containers > Resource types  
Original saved excerpt offsets: [148, 556)  
Snippet cut or saved source already truncated: False

```text
| Resource type | Description | Base unit |
| --- | --- | --- |
| `cpu` | Compute processing | cpu (core) |
| `memory` | RAM | Bytes |
| `ephemeral-storage` | [Local ephemeral storage](https://kubernetes.io/docs/concepts/storage/ephemeral-storage/) | Bytes |
| `hugepages-<size>` | [Huge pages](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/#huge-pages) (Linux only) | Bytes |
```

### E2 — conf-004-sec-006-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/  
Heading: Resource Management for Pods and Containers > Resource types > Huge pages > Note:  
Original saved excerpt offsets: [12, 95)  
Snippet cut or saved source already truncated: False

```text
CPU and memory are collectively referred to as *compute resources*, or *resources*.
```

### E3 — conf-004-sec-006-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/  
Heading: Resource Management for Pods and Containers > Resource types > Huge pages > Note:  
Original saved excerpt offsets: [290, 475)  
Snippet cut or saved source already truncated: False

```text
API resources, such as Pods and
[Services](https://kubernetes.io/docs/concepts/services-networking/service/) are objects that can be read and modified
through the Kubernetes API server.
```

### E4 — conf-004-sec-015-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/  
Heading: Resource Management for Pods and Containers > How Pods with resource requests are scheduled  
Original saved excerpt offsets: [136, 254)  
Snippet cut or saved source already truncated: False

```text
Each node has a maximum capacity for each of the resource types: the
amount of CPU and memory it can provide for Pods.
```

### E5 — conf-004-sec-008-ch-001 (retrieval rank 4)

Source: https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/  
Heading: Resource Management for Pods and Containers > Pod-level resource specification  
Original saved excerpt offsets: [256, 406)  
Snippet cut or saved source already truncated: False

```text
At the Pod level, Kubernetes 1.37
only supports resource requests or limits for specific resource types: `cpu` and /
or `memory` and / or `hugepages`.
```

### E6 — conf-004-sec-008-ch-001 (retrieval rank 4)

Source: https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/  
Heading: Resource Management for Pods and Containers > Pod-level resource specification  
Original saved excerpt offsets: [874, 1079)  
Snippet cut or saved source already truncated: False

```text
- spec.resources.limits.cpu
- spec.resources.limits.memory
- spec.resources.limits.hugepages-<size>
- spec.resources.requests.cpu
- spec.resources.requests.memory
- spec.resources.requests.hugepages-<size>
```

---

## k8s-009

**Question:** You want Pod affinity to match existing Pods using the value of a label on the incoming Pod, without hard-coding that label value in the selector. Which field should you use and how is it applied?

### E1 — sched-003-sec-022-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/  
Heading: Assigning Pods to Nodes > Affinity and anti-affinity > Inter-pod affinity and anti-affinity > Note:  
Original saved excerpt offsets: [528, 815)  
Snippet cut or saved source already truncated: False

```text
The keys are used to look up values from the Pod labels; those key-value labels are combined
(using `AND`) with the match restrictions defined using the `labelSelector` field. The combined
filtering selects the set of existing Pods that will be taken into Pod (anti)affinity calculation.
```

### E2 — sched-003-sec-023-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/  
Heading: Assigning Pods to Nodes > Affinity and anti-affinity > Inter-pod affinity and anti-affinity > Caution:  
Original saved excerpt offsets: [15, 354)  
Snippet cut or saved source already truncated: False

```text
A common use case is to use `matchLabelKeys` with `pod-template-hash` (set on Pods
managed as part of a Deployment, where the value is unique for each revision).
Using `pod-template-hash` in `matchLabelKeys` allows you to target the Pods that belong
to the same revision as the incoming Pod, so that a rolling upgrade won't break affinity.
```

### E3 — sched-003-sec-020-ch-001 (retrieval rank 2)

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

### E4 — sched-003-sec-022-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/  
Heading: Assigning Pods to Nodes > Affinity and anti-affinity > Inter-pod affinity and anti-affinity > Note:  
Original saved excerpt offsets: [12, 305)  
Snippet cut or saved source already truncated: False

```text
The `matchLabelKeys` field is a beta-level field and is enabled by default in
Kubernetes 1.37.
When you want to disable it, you have to disable it explicitly via the
`MatchLabelKeysInPodAffinity` [feature gate](https://kubernetes.io/docs/reference/command-line-tools-reference/feature-gates/).
```

### E5 — sched-003-sec-025-ch-001 (retrieval rank 4)

Source: https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/  
Heading: Assigning Pods to Nodes > Affinity and anti-affinity > Inter-pod affinity and anti-affinity > Note:  
Original saved excerpt offsets: [12, 308)  
Snippet cut or saved source already truncated: False

```text
The `mismatchLabelKeys` field is a beta-level field and is enabled by default in
Kubernetes 1.37.
When you want to disable it, you have to disable it explicitly via the
`MatchLabelKeysInPodAffinity` [feature gate](https://kubernetes.io/docs/reference/command-line-tools-reference/feature-gates/).
```

### E6 — sched-003-sec-025-ch-001 (retrieval rank 4)

Source: https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/  
Heading: Assigning Pods to Nodes > Affinity and anti-affinity > Inter-pod affinity and anti-affinity > Note:  
Original saved excerpt offsets: [310, 536)  
Snippet cut or saved source already truncated: False

```text
Kubernetes includes an optional `mismatchLabelKeys` field for Pod affinity
or anti-affinity. The field specifies keys for the labels that should not match with the incoming Pod's labels,
when satisfying the Pod (anti)affinity.
```

---

## k8s-010

**Question:** If a namespace is exempted from Pod Security Admission, what checks are skipped, and why should administrators still be cautious about who can create workloads in that namespace?

### E1 — sec-002-sec-014-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/security/pod-security-standards/  
Heading: Pod Security Standards > User namespaces  
Original saved excerpt offsets: [20, 341)  
Snippet cut or saved source already truncated: False

```text
User Namespaces are a Linux-only feature to run workloads with increased
isolation. How they work together with Pod Security Standards is described in
the [documentation](https://kubernetes.io/docs/concepts/workloads/pods/user-namespaces/#integration-with-pod-security-admission-checks) for Pods that use user namespaces.
```

### E2 — sec-006-sec-009-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/security/rbac-good-practices/  
Heading: Role Based Access Control Good Practices > Kubernetes RBAC - privilege escalation risks > Workload creation  
Original saved excerpt offsets: [23, 332)  
Snippet cut or saved source already truncated: False

```text
Permission to create workloads (either Pods, or
[workload resources](https://kubernetes.io/docs/concepts/workloads/controllers/) that manage Pods) in a namespace
implicitly grants access to many other resources in that namespace, such as Secrets, ConfigMaps, and
PersistentVolumes that can be mounted in Pods.
```

### E3 — sec-006-sec-009-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/security/rbac-good-practices/  
Heading: Role Based Access Control Good Practices > Kubernetes RBAC - privilege escalation risks > Workload creation  
Original saved excerpt offsets: [333, 598)  
Snippet cut or saved source already truncated: False

```text
Additionally, since Pods can run as any
[ServiceAccount](https://kubernetes.io/docs/reference/access-authn-authz/service-accounts-admin/), granting permission
to create workloads also implicitly grants the API access levels of any service account in that
namespace.
```

### E4 — sec-003-sec-006-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/security/pod-security-admission/  
Heading: Pod Security Admission > Exemptions  
Original saved excerpt offsets: [15, 424)  
Snippet cut or saved source already truncated: False

```text
You can define *exemptions* from pod security enforcement in order to allow the creation of pods that
would have otherwise been prohibited due to the policy associated with a given namespace.
Exemptions can be statically configured in the
[Admission Controller configuration](https://kubernetes.io/docs/tasks/configure-pod-container/enforce-standards-admission-controller/#configure-the-admission-controller).
```

### E5 — sec-003-sec-004-ch-001 (retrieval rank 4)

Source: https://kubernetes.io/docs/concepts/security/pod-security-admission/  
Heading: Pod Security Admission > Pod Security Admission labels for namespaces  
Original saved excerpt offsets: [49, 223)  
Snippet cut or saved source already truncated: True

```text
Once the feature is enabled or the webhook is installed, you can configure namespaces to define the admission
control mode you want to use for pod security in each namespace.
```

### E6 — sec-003-sec-006-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/security/pod-security-admission/  
Heading: Pod Security Admission > Exemptions  
Original saved excerpt offsets: [426, 634)  
Snippet cut or saved source already truncated: False

```text
Exemptions must be explicitly enumerated. Requests meeting exemption criteria are *ignored* by the
Admission Controller (all `enforce`, `audit` and `warn` behaviors are skipped). Exemption dimensions include:
```

---

## k8s-011

**Question:** An Ingress is being handled by the wrong controller. What should you check in the Ingress and IngressClass configuration?

### E1 — net-003-sec-015-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/services-networking/ingress/  
Heading: Ingress > Ingress class  
Original saved excerpt offsets: [18, 294)  
Snippet cut or saved source already truncated: False

```text
Ingresses can be implemented by different controllers, often with different
configuration. Each Ingress should specify a class, a reference to an
IngressClass resource that contains additional configuration including the name
of the controller that should implement the class.
```

### E2 — net-003-sec-015-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/services-networking/ingress/  
Heading: Ingress > Ingress class  
Original saved excerpt offsets: [536, 677)  
Snippet cut or saved source already truncated: False

```text
The `.spec.parameters` field of an IngressClass lets you reference another
resource that provides configuration related to that IngressClass.
```

### E3 — net-003-sec-005-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/services-networking/ingress/  
Heading: Ingress > Prerequisites  
Original saved excerpt offsets: [18, 205)  
Snippet cut or saved source already truncated: False

```text
You must have an [Ingress controller](https://kubernetes.io/docs/concepts/services-networking/ingress-controllers/)
to satisfy an Ingress. Only creating an Ingress resource has no effect.
```

### E4 — net-003-sec-019-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/services-networking/ingress/  
Heading: Ingress > Ingress class > Default IngressClass > Caution:  
Original saved excerpt offsets: [15, 119)  
Snippet cut or saved source already truncated: False

```text
Start by defining a
default IngressClass. It is recommended though, to specify the default
IngressClass:
```

### E5 — net-003-sec-016-ch-002 (retrieval rank 4)

Source: https://kubernetes.io/docs/concepts/services-networking/ingress/  
Heading: Ingress > Ingress class > IngressClass scope  
Original saved excerpt offsets: [286, 339)  
Snippet cut or saved source already truncated: False

```text
The IngressClass API itself is always cluster-scoped.
```

### E6 — net-003-sec-016-ch-002 (retrieval rank 4)

Source: https://kubernetes.io/docs/concepts/services-networking/ingress/  
Heading: Ingress > Ingress class > IngressClass scope  
Original saved excerpt offsets: [341, 425)  
Snippet cut or saved source already truncated: False

```text
Here is an example of an IngressClass that refers to parameters that are
namespaced:
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

## k8s-013

**Question:** Which three probe types does the Pod Lifecycle documentation recommend configuring for hands-on experience?

### E1 — work-003-sec-049-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/  
Heading: Pod Lifecycle > What's next  
Original saved excerpt offsets: [16, 406)  
Snippet cut or saved source already truncated: True

```text
- Get hands-on experience [attaching handlers to container lifecycle events](https://kubernetes.io/docs/tasks/configure-pod-container/attach-handler-lifecycle-event/).
- Get hands-on experience [configuring Liveness, Readiness and Startup Probes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/).
- Learn more about [container lifecycle
```

### E2 — work-003-sec-049-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/  
Heading: Pod Lifecycle > What's next  
Original saved excerpt offsets: [407, 827)  
Snippet cut or saved source already truncated: True

```text
hooks](https://kubernetes.io/docs/concepts/containers/container-lifecycle-hooks/).
- Learn more about [sidecar containers](https://kubernetes.io/docs/concepts/workloads/pods/sidecar-containers/).
- For detailed information about Pod and container status in the API, see the API reference documentation covering [`status`](https://kubernetes.io/docs/reference/kubernetes-api/workload-resources/pod-v1/#PodStatus) for Pod.
```

### E3 — work-015-sec-025-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/configuration/liveness-readiness-startup-probes/  
Heading: Liveness, Readiness, and Startup Probes > What's next  
Original saved excerpt offsets: [16, 182)  
Snippet cut or saved source already truncated: False

```text
- Learn how to Configure Liveness, Readiness and Startup Probes .
- For the full specification of probe-related fields, see the API reference: Pod , Container , Probe
```

### E4 — work-015-sec-009-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/configuration/liveness-readiness-startup-probes/  
Heading: Liveness, Readiness, and Startup Probes > When to use each probe > When should you use a startup probe?  
Original saved excerpt offsets: [334, 762)  
Snippet cut or saved source already truncated: False

```text
If your container usually starts in more than
\( initialDelaySeconds + failureThreshold \times periodSeconds \), you should specify a
startup probe that checks the same endpoint as the liveness probe. The default
for `periodSeconds` is 10s. You should then set its `failureThreshold` high
enough to allow the container to start, without changing the default values of
the liveness probe. This helps to protect against deadlocks.
```

### E5 — work-003-sec-037-ch-001 (retrieval rank 4)

Source: https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/  
Heading: Pod Lifecycle > Container probes > Readiness probe  
Original saved excerpt offsets: [396, 636)  
Snippet cut or saved source already truncated: False

```text
If the readiness probe returns a failed state, the
[EndpointSlice](https://kubernetes.io/docs/concepts/services-networking/endpoint-slices/)
controller removes the Pod's IP address from the EndpointSlices of all Services
that match the Pod.
```

### E6 — work-003-sec-037-ch-001 (retrieval rank 4)

Source: https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/  
Heading: Pod Lifecycle > Container probes > Readiness probe  
Original saved excerpt offsets: [21, 394)  
Snippet cut or saved source already truncated: False

```text
Readiness probes determine when a container is ready to accept traffic.
This is useful when waiting for an application to perform time-consuming initial
tasks, such as establishing network connections, loading files, and warming
caches.
Readiness probes can also be useful later in the container's lifecycle,
for example, when recovering from temporary faults or overloads.
```

---

## k8s-014

**Question:** How do Kubernetes built-in controllers differ from the cloud-controller-manager in where they run and what responsibilities they provide?

### E1 — arch-004-sec-008-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/architecture/controller/  
Heading: Controllers > Ways of running controllers  
Original saved excerpt offsets: [32, 283)  
Snippet cut or saved source already truncated: False

```text
Kubernetes comes with a set of built-in controllers that run inside
the [kube-controller-manager](https://kubernetes.io/docs/reference/command-line-tools-reference/kube-controller-manager/). These
built-in controllers provide important core behaviors.
```

### E2 — arch-004-sec-008-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/architecture/controller/  
Heading: Controllers > Ways of running controllers  
Original saved excerpt offsets: [285, 589)  
Snippet cut or saved source already truncated: False

```text
The Deployment controller and Job controller are examples of controllers that
come as part of Kubernetes itself ("built-in" controllers).
Kubernetes lets you run a resilient control plane, so that if any of the built-in
controllers were to fail, another part of the control plane will take over the work.
```

### E3 — arch-007-sec-002-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/architecture/cloud-controller/  
Heading: Cloud Controller Manager > Design  
Original saved excerpt offsets: [43, 318)  
Snippet cut or saved source already truncated: False

```text
The cloud controller manager runs in the control plane as a replicated set of processes
(usually, these are containers in Pods). Each cloud-controller-manager implements
multiple [controllers](https://kubernetes.io/docs/concepts/architecture/controller/) in a single
process.
```

### E4 — arch-007-sec-013-ch-001 (retrieval rank 4)

Source: https://kubernetes.io/docs/concepts/architecture/cloud-controller/  
Heading: Cloud Controller Manager > What's next  
Original saved excerpt offsets: [466, 912)  
Snippet cut or saved source already truncated: True

```text
- Want to know how to implement your own cloud controller manager, or extend an existing project?
- The cloud controller manager uses Go interfaces, specifically, CloudProvider interface defined in `cloud.go` from kubernetes/cloud-provider to allow implementations from any cloud to be plugged in.
  - The implementation of the shared controllers highlighted in this document (Node, Route, and Service), and some scaffolding along with the shared
```

### E5 — arch-007-sec-001-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/architecture/cloud-controller/  
Heading: Cloud Controller Manager  
Original saved excerpt offsets: [228, 630)  
Snippet cut or saved source already truncated: False

```text
The cloud-controller-manager is a Kubernetes [control plane](https://kubernetes.io/docs/reference/glossary/?all=true#term-control-plane) component
that embeds cloud-specific control logic. The cloud controller manager lets you link your
cluster into your cloud provider's API, and separates out the components that interact
with that cloud platform from components that only interact with your cluster.
```

### E6 — arch-007-sec-001-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/architecture/cloud-controller/  
Heading: Cloud Controller Manager  
Original saved excerpt offsets: [632, 876)  
Snippet cut or saved source already truncated: False

```text
By decoupling the interoperability logic between Kubernetes and the underlying cloud
infrastructure, the cloud-controller-manager component enables cloud providers to release
features at a different pace compared to the main Kubernetes project.
```

---

## k8s-015

**Question:** You need to store a username and password for HTTP basic authentication in a Kubernetes Secret. Which Secret type and keys should you use?

### E1 — conf-003-sec-015-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/configuration/secret/  
Heading: Secrets > Types of Secret > Basic authentication Secret  
Original saved excerpt offsets: [33, 241)  
Snippet cut or saved source already truncated: False

```text
The `kubernetes.io/basic-auth` type is provided for storing credentials needed
for basic authentication. When using this Secret type, the `data` field of the
Secret must contain one of the following two keys:
```

### E2 — conf-003-sec-017-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/configuration/secret/  
Heading: Secrets > Types of Secret > SSH authentication Secrets  
Original saved excerpt offsets: [597, 1018)  
Snippet cut or saved source already truncated: False

```text
The SSH authentication Secret type is provided only for convenience.
You can create an `Opaque` type for credentials used for SSH authentication.
However, using the defined and public Secret type (`kubernetes.io/ssh-auth`) helps other
people to understand the purpose of your Secret, and sets a convention for what key names
to expect.
The Kubernetes API verifies that the required keys are set for a Secret of this type.
```

### E3 — conf-003-sec-016-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/configuration/secret/  
Heading: Secrets > Types of Secret > Basic authentication Secret > Note:  
Original saved excerpt offsets: [12, 353)  
Snippet cut or saved source already truncated: False

```text
The basic authentication Secret type is provided only for convenience.
You can create an `Opaque` type for credentials used for basic authentication.
However, using the defined and public Secret type (`kubernetes.io/basic-auth`) helps other
people to understand the purpose of your Secret, and sets a convention for what key names
to expect.
```

### E4 — conf-003-sec-015-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/configuration/secret/  
Heading: Secrets > Types of Secret > Basic authentication Secret  
Original saved excerpt offsets: [243, 342)  
Snippet cut or saved source already truncated: False

```text
- username : the user name for authentication
- password : the password or token for authentication
```

### E5 — conf-003-sec-017-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/configuration/secret/  
Heading: Secrets > Types of Secret > SSH authentication Secrets  
Original saved excerpt offsets: [32, 286)  
Snippet cut or saved source already truncated: False

```text
The builtin type `kubernetes.io/ssh-auth` is provided for storing data used in
SSH authentication. When using this Secret type, you will have to specify a
`ssh-privatekey` key-value pair in the `data` (or `stringData`) field
as the SSH credential to use.
```

### E6 — sec-005-sec-003-ch-001 (retrieval rank 4)

Source: https://kubernetes.io/docs/concepts/security/controlling-access/  
Heading: Controlling Access to the Kubernetes API > Authentication  
Original saved excerpt offsets: [799, 1124)  
Snippet cut or saved source already truncated: False

```text
If the request cannot be authenticated, it is rejected with HTTP status code 401.
Otherwise, the user is authenticated as a specific `username`, and the user name
is available to subsequent steps to use in their decisions. Some authenticators
also provide the group memberships of the user, while other authenticators
do not.
```

---

## k8s-016

**Question:** A high-priority pending Pod preempts lower-priority Pods on a node and gets a `nominatedNodeName`. Is it guaranteed to run on that node, and what can change the nomination?

### E1 — sched-003-sec-030-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/  
Heading: Assigning Pods to Nodes > nominatedNodeName  
Original saved excerpt offsets: [22, 232)  
Snippet cut or saved source already truncated: False

```text
`nominatedNodeName` can be used for external components to nominate node for a pending pod.
This nomination is best effort: it might be ignored if the scheduler determines the pod cannot go to a nominated node.
```

### E2 — sched-006-sec-016-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/scheduling-eviction/pod-priority-preemption/  
Heading: Pod Priority and Preemption > Preemption > User exposed information  
Original saved excerpt offsets: [30, 287)  
Snippet cut or saved source already truncated: False

```text
When Pod P preempts one or more Pods on Node N, `nominatedNodeName` field of Pod
P's status is set to the name of Node N. This field helps the scheduler track
resources reserved for Pod P and also gives users information about preemptions
in their clusters.
```

### E3 — sched-006-sec-028-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/scheduling-eviction/pod-priority-preemption/  
Heading: Pod Priority and Preemption > Troubleshooting > Higher priority Pods are preempted before lower priority pods  
Original saved excerpt offsets: [271, 464)  
Snippet cut or saved source already truncated: False

```text
If a node with low priority Pods is not feasible to run the pending Pod, the scheduler
may choose another node with higher priority Pods (compared to the Pods on the
other node) for preemption.
```

### E4 — sched-006-sec-028-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/scheduling-eviction/pod-priority-preemption/  
Heading: Pod Priority and Preemption > Troubleshooting > Higher priority Pods are preempted before lower priority pods  
Original saved excerpt offsets: [129, 270)  
Snippet cut or saved source already truncated: False

```text
If no node is
found, the scheduler tries to remove Pods with lower priority from an arbitrary
node in order to make room for the pending pod.
```

### E5 — sched-006-sec-021-ch-001 (retrieval rank 4)

Source: https://kubernetes.io/docs/concepts/scheduling-eviction/pod-priority-preemption/  
Heading: Pod Priority and Preemption > Preemption > Limitations of preemption > Note:  
Original saved excerpt offsets: [12, 302)  
Snippet cut or saved source already truncated: False

```text
If a pending Pod has inter-pod [affinity](https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/#affinity-and-anti-affinity)
to one or more of the lower-priority Pods on the Node, the inter-Pod affinity
rule cannot be satisfied in the absence of those lower-priority Pods.
```

### E6 — sched-006-sec-016-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/scheduling-eviction/pod-priority-preemption/  
Heading: Pod Priority and Preemption > Preemption > User exposed information  
Original saved excerpt offsets: [761, 921)  
Snippet cut or saved source already truncated: False

```text
Also, if
the scheduler preempts Pods on Node N, but then a higher priority Pod than Pod P
arrives, the scheduler may give Node N to the new higher priority Pod.
```

---

## k8s-017

**Question:** A security review finds powerful service-account credentials available to privileged workloads that share nodes with untrusted Pods. What changes can reduce the blast radius?

### E1 — sec-006-sec-004-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/security/rbac-good-practices/  
Heading: Role Based Access Control Good Practices > General good practice > Minimize distribution of privileged tokens  
Original saved excerpt offsets: [458, 663)  
Snippet cut or saved source already truncated: False

```text
Ensure that any DaemonSets you run are necessary and are run with least privilege to limit the blast radius of container escapes.
- Avoid running powerful pods alongside untrusted or publicly-exposed ones.
```

### E2 — sec-006-sec-005-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/security/rbac-good-practices/  
Heading: Role Based Access Control Good Practices > General good practice > Hardening  
Original saved excerpt offsets: [321, 598)  
Snippet cut or saved source already truncated: False

```text
- Review bindings for the system:unauthenticated group and remove them where possible, as this gives access to anyone who can contact the API server at a network level.
- Avoid the default auto-mounting of service account tokens by setting automountServiceAccountToken: false .
```

### E3 — sec-006-sec-005-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/security/rbac-good-practices/  
Heading: Role Based Access Control Good Practices > General good practice > Hardening  
Original saved excerpt offsets: [659, 800)  
Snippet cut or saved source already truncated: False

```text
Setting this value for a Pod will overwrite the service account setting, workloads which require service account tokens can still mount them.
```

### E4 — sec-006-sec-009-ch-001 (retrieval rank 4)

Source: https://kubernetes.io/docs/concepts/security/rbac-good-practices/  
Heading: Role Based Access Control Good Practices > Kubernetes RBAC - privilege escalation risks > Workload creation  
Original saved excerpt offsets: [333, 598)  
Snippet cut or saved source already truncated: False

```text
Additionally, since Pods can run as any
[ServiceAccount](https://kubernetes.io/docs/reference/access-authn-authz/service-accounts-admin/), granting permission
to create workloads also implicitly grants the API access levels of any service account in that
namespace.
```

### E5 — sec-006-sec-004-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/security/rbac-good-practices/  
Heading: Role Based Access Control Good Practices > General good practice > Minimize distribution of privileged tokens  
Original saved excerpt offsets: [48, 405)  
Snippet cut or saved source already truncated: False

```text
Ideally, pods shouldn't be assigned service accounts that have been granted powerful permissions
(for example, any of the rights listed under [privilege escalation risks](https://kubernetes.io/docs/concepts/security/rbac-good-practices/#privilege-escalation-risks)).
In cases where a workload requires powerful permissions, consider the following practices:
```

### E6 — sec-006-sec-009-ch-001 (retrieval rank 4)

Source: https://kubernetes.io/docs/concepts/security/rbac-good-practices/  
Heading: Role Based Access Control Good Practices > Kubernetes RBAC - privilege escalation risks > Workload creation  
Original saved excerpt offsets: [600, 726)  
Snippet cut or saved source already truncated: False

```text
Users who can run privileged Pods can use that access to gain node access and potentially to
further elevate their privileges.
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

## k8s-019

**Question:** What does `allowedTopologies` do in a StorageClass using `WaitForFirstConsumer`, and when is it usually unnecessary?

### E1 — stor-006-sec-012-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/storage/storage-classes/  
Heading: Storage Classes > Allowed topologies  
Original saved excerpt offsets: [23, 264)  
Snippet cut or saved source already truncated: False

```text
When a cluster operator specifies the `WaitForFirstConsumer` volume binding mode, it is no longer necessary
to restrict provisioning to specific topologies in most situations. However,
if still required, `allowedTopologies` can be specified.
```

### E2 — stor-006-sec-025-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/storage/storage-classes/  
Heading: Storage Classes > Parameters > Local  
Original saved excerpt offsets: [262, 530)  
Snippet cut or saved source already truncated: False

```text
Local volumes do not support dynamic provisioning in Kubernetes 1.37;
however a StorageClass should still be created to delay volume binding until a Pod is actually
scheduled to the appropriate node. This is specified by the `WaitForFirstConsumer` volume
binding mode.
```

### E3 — stor-003-sec-051-ch-001 (retrieval rank 4)

Source: https://kubernetes.io/docs/concepts/storage/persistent-volumes/  
Heading: Persistent Volumes > PersistentVolumeClaims > Class > Retroactive default StorageClass assignment  
Original saved excerpt offsets: [1011, 1372)  
Snippet cut or saved source already truncated: False

```text
This behavior helps administrators change default StorageClass by removing the
old one first and then creating or setting another one. This brief window while
there is no default causes PVCs without `storageClassName` created at that time
to not have any default, but due to the retroactive default StorageClass
assignment this way of changing defaults is safe.
```

### E4 — stor-003-sec-049-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/storage/persistent-volumes/  
Heading: Persistent Volumes > PersistentVolumeClaims > Class  
Original saved excerpt offsets: [11, 302)  
Snippet cut or saved source already truncated: True

```text
A claim can request a particular class by specifying the name of a
[StorageClass](https://kubernetes.io/docs/concepts/storage/storage-classes/)
using the attribute `storageClassName`.
Only PVs of the requested class, ones with the same `storageClassName` as the PVC,
can be bound to the PVC.
```

### E5 — stor-003-sec-049-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/storage/persistent-volumes/  
Heading: Persistent Volumes > PersistentVolumeClaims > Class  
Original saved excerpt offsets: [352, 549)  
Snippet cut or saved source already truncated: True

```text
A PVC with its `storageClassName` set
equal to `""` is always interpreted to be requesting a PV with no class, so it
can only be bound to PVs with no class (no annotation or one set equal to `""`).
```

### E6 — stor-003-sec-051-ch-001 (retrieval rank 4)

Source: https://kubernetes.io/docs/concepts/storage/persistent-volumes/  
Heading: Persistent Volumes > PersistentVolumeClaims > Class > Retroactive default StorageClass assignment  
Original saved excerpt offsets: [50, 360)  
Snippet cut or saved source already truncated: False

```text
You can create a PersistentVolumeClaim without specifying a `storageClassName`
for the new PVC, and you can do so even when no default StorageClass exists
in your cluster. In this case, the new PVC creates as you defined it, and the
`storageClassName` of that PVC remains unset until default becomes available.
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

## k8s-021

**Question:** A worker node is running Pods, but the node is not programming the network rules needed to implement Kubernetes Services. Which node component is responsible for that function?

### E1 — arch-001-sec-004-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/overview/components/  
Heading: Kubernetes Components > Core Components > Node Components  
Original saved excerpt offsets: [250, 465)  
Snippet cut or saved source already truncated: False

```text
**[kube-proxy](https://kubernetes.io/docs/concepts/architecture/#kube-proxy) (optional)**
: Maintains network rules on nodes to implement [Services](https://kubernetes.io/docs/concepts/services-networking/service/).
```

### E2 — net-001-sec-002-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/services-networking/  
Heading: Services, Load Balancing, and Networking > The Kubernetes network model  
Original saved excerpt offsets: [845, 1291)  
Snippet cut or saved source already truncated: True

```text
On Windows, this rule does not apply to host-network pods.
  - Agents on a node (such as system daemons, or kubelet) can communicate with all pods on that node.
- The [Service](https://kubernetes.io/docs/concepts/services-networking/service/) API lets you provide a stable (long lived) IP address or hostname for a service implemented by one or more backend pods, where the individual pods making up the service can change over time.
- Kubernetes
```

### E3 — arch-001-sec-004-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/overview/components/  
Heading: Kubernetes Components > Core Components > Node Components  
Original saved excerpt offsets: [466, 605)  
Snippet cut or saved source already truncated: False

```text
**[Container runtime](https://kubernetes.io/docs/concepts/architecture/#container-runtime)**
: Software responsible for running containers.
```

### E4 — work-012-sec-010-ch-002 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/workloads/controllers/daemonset/  
Heading: DaemonSet > How Daemon Pods are scheduled > Taints and tolerations  
Original saved excerpt offsets: [871, 1147)  
Snippet cut or saved source already truncated: False

```text
For example, without that special toleration, you could end up in a deadlock
situation where the node is not marked as ready because the network plugin is
not running there, and at the same time the network plugin is not running on
that node because the node is not yet ready.
```

### E5 — work-012-sec-010-ch-002 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/workloads/controllers/daemonset/  
Heading: DaemonSet > How Daemon Pods are scheduled > Taints and tolerations  
Original saved excerpt offsets: [617, 870)  
Snippet cut or saved source already truncated: False

```text
If you use a DaemonSet to provide an important node-level function, such as
[cluster networking](https://kubernetes.io/docs/concepts/cluster-administration/networking/), it is
helpful that Kubernetes places DaemonSet Pods on nodes before they are ready.
```

### E6 — net-001-sec-002-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/services-networking/  
Heading: Services, Load Balancing, and Networking > The Kubernetes network model  
Original saved excerpt offsets: [322, 516)  
Snippet cut or saved source already truncated: True

```text
Processes running in different containers in the same pod can communicate with each other over localhost .
- The *pod network* (also called a cluster network) handles communication between pods.
```

---

## k8s-022

**Question:** How do container resource requests and limits contribute to a Pod's overall resource values, and how are requests and limits used differently while the Pod is scheduled and running?

**No retriever passages were recorded for this question.** This does NOT establish that the question is unanswerable.

## k8s-023

**Question:** A running Pod requests an in-place resize, but an operator does not want the scheduler to evict lower-priority Pods on a particular node just to make room for that resize. What can the operator configure, and who performs the resize once capacity is available?

### E1 — conf-004-sec-019-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/  
Heading: Resource Management for Pods and Containers > How Kubernetes applies resource requests and limits > Resizing container resources > Note:  
Original saved excerpt offsets: [462, 863)  
Snippet cut or saved source already truncated: False

```text
When the `InPlacePodVerticalScalingSchedulerPreemption` feature gate is enabled,
deferred in-place resize requests can trigger `kube-scheduler` to preempt
lower-priority Pods on the assigned node to make room for the resize.
For more details, see
[Preemption for in-place Pod resize](https://kubernetes.io/docs/concepts/scheduling-eviction/pod-priority-preemption/#preemption-for-in-place-pod-resize).
```

### E2 — sched-006-sec-023-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/scheduling-eviction/pod-priority-preemption/  
Heading: Pod Priority and Preemption > Preemption > Preemption for in-place Pod resize  
Original saved excerpt offsets: [490, 939)  
Snippet cut or saved source already truncated: True

```text
When the `InPlacePodVerticalScalingSchedulerPreemption` feature gate is enabled,
preemption also applies when a running Pod's in-place resize request is `Deferred`
(meaning the requested resize is temporarily not possible, but might become
feasible later) due to insufficient node capacity.
For details on resize states, see
[Pod resize status](https://kubernetes.io/docs/tasks/configure-pod-container/resize-container-resources/#pod-resize-status).
```

### E3 — sched-006-sec-023-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/scheduling-eviction/pod-priority-preemption/  
Heading: Pod Priority and Preemption > Preemption > Preemption for in-place Pod resize  
Original saved excerpt offsets: [941, 1144)  
Snippet cut or saved source already truncated: True

```text
If a higher-priority Pod cannot be resized in-place because its node lacks
available CPU or memory, `kube-scheduler` attempts to preempt lower-priority Pods
on that node to free up the required capacity.
```

### E4 — sched-006-sec-024-ch-001 (retrieval rank 4)

Source: https://kubernetes.io/docs/concepts/scheduling-eviction/pod-priority-preemption/  
Heading: Pod Priority and Preemption > Preemption > Preemption for in-place Pod resize > Disabling preemption for in-place Pod resize at the Node level  
Original saved excerpt offsets: [69, 395)  
Snippet cut or saved source already truncated: False

```text
Cluster operators and controllers can disable scheduler-triggered preemption
caused by in-place Pod resize requests on specific nodes.
This is useful for resizable nodes or nodes with custom autoscaling solutions,
protecting existing workloads from disruption and allowing node-upsizing to
handle the resource deficit instead.
```

### E5 — sched-006-sec-024-ch-001 (retrieval rank 4)

Source: https://kubernetes.io/docs/concepts/scheduling-eviction/pod-priority-preemption/  
Heading: Pod Priority and Preemption > Preemption > Preemption for in-place Pod resize > Disabling preemption for in-place Pod resize at the Node level  
Original saved excerpt offsets: [397, 680)  
Snippet cut or saved source already truncated: False

```text
This is configured using the `spec.podPreemptionPolicy` field on the `Node` spec.
If the `disableResizePreemption` list is non-empty, resize-induced preemption
is disabled on that node, and `kube-scheduler` will skip preemption attempts
for any deferred resizes running on that node.
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

## k8s-026

**Question:** How does dynamic provisioning of a PersistentVolume differ from dynamically creating a VolumeSnapshot in terms of the class object that supplies provider-specific provisioning information?

### E1 — stor-008-sec-006-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/storage/volume-snapshots/  
Heading: Volume Snapshots > Lifecycle of a volume snapshot and volume snapshot content > Provisioning Volume Snapshot > Dynamic  
Original saved excerpt offsets: [14, 315)  
Snippet cut or saved source already truncated: False

```text
Instead of using a pre-existing snapshot, you can request that a snapshot to be dynamically
taken from a PersistentVolumeClaim. The [VolumeSnapshotClass](https://kubernetes.io/docs/concepts/storage/volume-snapshot-classes/)
specifies storage provider-specific parameters to use when taking a snapshot.
```

### E2 — stor-007-sec-001-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/storage/dynamic-provisioning/  
Heading: Dynamic Volume Provisioning  
Original saved excerpt offsets: [107, 396)  
Snippet cut or saved source already truncated: False

```text
Without dynamic provisioning, cluster administrators have to manually make
calls to their cloud or storage provider to create new storage volumes, and
then create [`PersistentVolume` objects](https://kubernetes.io/docs/concepts/storage/persistent-volumes/)
to represent them in Kubernetes.
```

### E3 — stor-007-sec-004-ch-001 (retrieval rank 4)

Source: https://kubernetes.io/docs/concepts/storage/dynamic-provisioning/  
Heading: Dynamic Volume Provisioning > Using Dynamic Provisioning  
Original saved excerpt offsets: [291, 395)  
Snippet cut or saved source already truncated: False

```text
Users now can and should instead use the
`storageClassName` field of the `PersistentVolumeClaim` object.
```

### E4 — stor-007-sec-004-ch-001 (retrieval rank 4)

Source: https://kubernetes.io/docs/concepts/storage/dynamic-provisioning/  
Heading: Dynamic Volume Provisioning > Using Dynamic Provisioning  
Original saved excerpt offsets: [31, 139)  
Snippet cut or saved source already truncated: False

```text
Users request dynamically provisioned storage by including a storage class in
their `PersistentVolumeClaim`.
```

### E5 — stor-003-sec-006-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/storage/persistent-volumes/  
Heading: Persistent Volumes > Lifecycle of a volume and claim > Provisioning > Dynamic  
Original saved excerpt offsets: [14, 182)  
Snippet cut or saved source already truncated: False

```text
When none of the static PVs the administrator created match a user's PersistentVolumeClaim,
the cluster may try to dynamically provision a volume specially for the PVC.
```

### E6 — stor-007-sec-001-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/storage/dynamic-provisioning/  
Heading: Dynamic Volume Provisioning  
Original saved excerpt offsets: [31, 106)  
Snippet cut or saved source already truncated: False

```text
Dynamic volume provisioning allows storage volumes to be created on-demand.
```

---

## k8s-027

**Question:** You are defining an eight-Pod distributed training Job where all eight Pods must be schedulable together, should be co-located in one zone, and should be disrupted as a group. How should the Job's scheduling configuration express those requirements?

### E1 — work-013-sec-013-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/workloads/controllers/job/  
Heading: Jobs > Integrate with Workload APIs > Gang scheduling  
Original saved excerpt offsets: [21, 136)  
Snippet cut or saved source already truncated: True

```text
The following Job requests gang scheduling for its 8 Pods, co-located within a
single zone, and disrupted together:
```

### E2 — work-013-sec-012-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/workloads/controllers/job/  
Heading: Jobs > Integrate with Workload APIs > Scheduling configuration  
Original saved excerpt offsets: [306, 516)  
Snippet cut or saved source already truncated: False

```text
See PodGroup scheduling policies .
- schedulingConstraints : topology co-location constraints for the Job's Pods.
- disruptionMode : whether the Pods are disrupted individually ( single ) or as a group ( all ).
```

### E3 — work-013-sec-012-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/workloads/controllers/job/  
Heading: Jobs > Integrate with Workload APIs > Scheduling configuration  
Original saved excerpt offsets: [159, 238)  
Snippet cut or saved source already truncated: False

```text
With gang , all Pods must be schedulable together before any of them are bound.
```

### E4 — work-001-sec-002-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/workloads/  
Heading: Workloads > Workload placement  
Original saved excerpt offsets: [415, 606)  
Snippet cut or saved source already truncated: False

```text
While standard workload resources (like Deployments and Jobs) manage the lifecycle of Pods,
you may have complex scheduling requirements where groups of Pods must be treated as a single unit.
```

### E5 — work-013-sec-013-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/workloads/controllers/job/  
Heading: Jobs > Integrate with Workload APIs > Gang scheduling  
Original saved excerpt offsets: [1255, 1520)  
Snippet cut or saved source already truncated: True

```text
The controller discovers these objects through spec references
(`Workload.spec.controllerRef` and `PodGroup.spec.workloadRef`), not by
name. Objects the controller creates carry an `ownerReferences` entry pointing to
the Job, so they are garbage [TRUNCATED EXCERPT]
```

### E6 — work-001-sec-002-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/workloads/  
Heading: Workloads > Workload placement  
Original saved excerpt offsets: [608, 891)  
Snippet cut or saved source already truncated: False

```text
The [Workload API](https://kubernetes.io/docs/concepts/workloads/workload-api/) allows you to define `PodGroupTemplates` to group Pods and apply advanced scheduling policies to them,
such as [gang scheduling](https://kubernetes.io/docs/concepts/scheduling-eviction/gang-scheduling/).
```

---

## k8s-028

**Question:** Why is re-registering a Node recommended when restarting its kubelet with a new set of node labels, and how can those label changes affect a DaemonSet?

### E1 — arch-002-sec-006-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/architecture/nodes/  
Heading: Nodes > Management > Self-registration of Nodes > Note:  
Original saved excerpt offsets: [483, 883)  
Snippet cut or saved source already truncated: False

```text
Pods already scheduled on the Node may misbehave or cause issues if the Node
configuration will be changed on kubelet restart. For example, an already running
Pod may be tainted against the new labels assigned to the Node, while other
Pods, that are incompatible with that Pod will be scheduled based on this new
label. Node re-registration ensures all Pods will be drained and properly
re-scheduled.
```

### E2 — arch-002-sec-006-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/architecture/nodes/  
Heading: Nodes > Management > Self-registration of Nodes > Note:  
Original saved excerpt offsets: [254, 481)  
Snippet cut or saved source already truncated: False

```text
For example, if the kubelet is being restarted with
a new set of `--node-labels`, but the same Node name is used, the change will
not take effect, as labels are only set (or modified) upon Node registration with the API server.
```

### E3 — work-009-sec-012-ch-001 (retrieval rank 4)

Source: https://kubernetes.io/docs/concepts/workloads/controllers/deployment/  
Heading: Deployments > Updating a Deployment > Label selector updates  
Original saved excerpt offsets: [1053, 1499)  
Snippet cut or saved source already truncated: True

```text
This is a non-overlapping change: the new Deployment will not "see" the old Pods (which lack the new label), causing the old ReplicaSet to be orphaned and a brand-new ReplicaSet to be created.
- Value Updates: Changing the existing value in a selector key (e.g., from v1 to v2 ) results in the same behavior as additions (orphaning and recreation).
- Removals: Removing an existing key from the Deployment selector does not require any changes in
```

### E4 — arch-002-sec-007-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/architecture/nodes/  
Heading: Nodes > Management > Manual Node administration  
Original saved excerpt offsets: [1028, 1246)  
Snippet cut or saved source already truncated: False

```text
Marking a node as unschedulable prevents the scheduler from placing new pods onto
that Node but does not affect existing Pods on the Node. This is useful as a
preparatory step before a node reboot or other maintenance.
```

### E5 — work-012-sec-012-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/workloads/controllers/daemonset/  
Heading: DaemonSet > Updating a DaemonSet  
Original saved excerpt offsets: [25, 160)  
Snippet cut or saved source already truncated: False

```text
If node labels are changed, the DaemonSet will promptly add Pods to newly matching nodes and delete
Pods from newly not-matching nodes.
```

### E6 — work-012-sec-012-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/workloads/controllers/daemonset/  
Heading: DaemonSet > Updating a DaemonSet  
Original saved excerpt offsets: [387, 706)  
Snippet cut or saved source already truncated: False

```text
You can delete a DaemonSet. If you specify `--cascade=orphan` with `kubectl`, then the Pods
will be left on the nodes. If you subsequently create a new DaemonSet with the same selector,
the new DaemonSet adopts the existing Pods. If any Pods need replacing the DaemonSet replaces
them according to its `updateStrategy`.
```

---

## k8s-029

**Question:** A workload needs a Pod specification change that cannot be handled by changing only the running containers' CPU or memory requests and limits. What is the portable Kubernetes approach to applying the change?

### E1 — conf-004-sec-020-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/  
Heading: Resource Management for Pods and Containers > How Kubernetes applies resource requests and limits > Resizing container resources > Resizing by launching replacement Pods  
Original saved excerpt offsets: [45, 371)  
Snippet cut or saved source already truncated: False

```text
The cloud native approach to changing a Pod's resources is to update the Pod template
in the workload object (such as a Deployment or StatefulSet) and let the workload's
controller replace Pods with new ones that have the updated resources. This approach
works with any Kubernetes version and can change any Pod specification.
```

### E2 — conf-004-sec-008-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/  
Heading: Resource Management for Pods and Containers > Pod-level resource specification  
Original saved excerpt offsets: [256, 406)  
Snippet cut or saved source already truncated: False

```text
At the Pod level, Kubernetes 1.37
only supports resource requests or limits for specific resource types: `cpu` and /
or `memory` and / or `hugepages`.
```

### E3 — work-003-sec-033-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/  
Heading: Pod Lifecycle > Resizing Pods > Resizing by launching replacement Pods  
Original saved excerpt offsets: [44, 389)  
Snippet cut or saved source already truncated: False

```text
The more cloud native approach to changing a Pod's resources is through the
workload resource that manages it (such as a Deployment or StatefulSet).
When you update the resource specifications in the Pod template,
the workload's controller creates new Pods with the updated resources and terminates
the old Pods according to its update strategy.
```

### E4 — work-003-sec-033-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/  
Heading: Pod Lifecycle > Resizing Pods > Resizing by launching replacement Pods  
Original saved excerpt offsets: [407, 720)  
Snippet cut or saved source already truncated: False

```text
- Works with any Kubernetes version.
- Can change any Pod specification, not just resources.
- Results in Pod replacement, so you should design your workload to handle planned disruptions . Consider using a PodDisruptionBudget to control availability.
- Requires that your Pods are managed by a workload resource.
```

### E5 — conf-004-sec-008-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/  
Heading: Resource Management for Pods and Containers > Pod-level resource specification  
Original saved excerpt offsets: [770, 872)  
Snippet cut or saved source already truncated: False

```text
For a Pod, you can specify resource limits and requests for CPU and memory by including the following:
```

### E6 — work-002-sec-022-ch-001 (retrieval rank 4)

Source: https://kubernetes.io/docs/concepts/workloads/pods/  
Heading: Pods > Resource requests and limits  
Original saved excerpt offsets: [193, 525)  
Snippet cut or saved source already truncated: False

```text
When you specify the resource *request* for containers in a Pod, the
kube-scheduler uses this information to decide which node to place the Pod on.
When you specify a resource *limit* for a container, the kubelet enforces
those limits so that the running container is not allowed to use more of that
resource than the limit you set.
```

---

## k8s-033

**Question:** A Linux container mounts `/mnt` from the host with `readOnly: true`, but a separate filesystem mounted underneath `/mnt` is still writable from the container. How can you request that the whole mount tree be read-only?

### E1 — stor-002-sec-058-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/storage/volumes/  
Heading: Volumes > Read-only mounts  
Original saved excerpt offsets: [309, 707)  
Snippet cut or saved source already truncated: False

```text
On Linux, read-only mounts are not recursively read-only by default.
For example, consider a Pod that mounts the hosts `/mnt` as a `hostPath` volume. If
there is another filesystem mounted read-write on `/mnt/<SUBMOUNT>` (such as tmpfs,
NFS, or USB storage), the volume mounted into the container(s) will also have a writeable
`/mnt/<SUBMOUNT>`, even if the mount itself was specified as read-only.
```

### E2 — stor-002-sec-059-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/storage/volumes/  
Heading: Volumes > Read-only mounts > Recursive read-only mounts  
Original saved excerpt offsets: [787, 1233)  
Snippet cut or saved source already truncated: True

```text
Needs all the following requirements to be satisfied: It will fail if any of these is not true.
- readOnly is set to true
  - mountPropagation is unset, or set to None
  - The host is running with Linux kernel v5.12 or later
  - The CRI-level container runtime supports recursive read-only mounts
  - The OCI-level container runtime supports recursive read-only mounts.
- `IfPossible`: attempts to apply `Enabled`, and falls back to `Disabled` if
```

### E3 — stor-002-sec-058-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/storage/volumes/  
Heading: Volumes > Read-only mounts  
Original saved excerpt offsets: [21, 307)  
Snippet cut or saved source already truncated: False

```text
A mount can be made read-only by setting the `.spec.containers[*].volumeMounts[*].readOnly`
field to `true`.
This does not make the volume itself read-only, but that specific container will
not be able to write to it.
Other containers in the Pod may mount the same volume as read-write.
```

### E4 — stor-002-sec-059-ch-002 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/storage/volumes/  
Heading: Volumes > Read-only mounts > Recursive read-only mounts  
Original saved excerpt offsets: [0, 225)  
Snippet cut or saved source already truncated: False

````text
recursiveReadOnly: Enabled
        # /mnt-ro/tmpfs is writable
        - name: mnt
          mountPath: /mnt-ro
          readOnly: true
        # /mnt-rw/tmpfs is writable
        - name: mnt
          mountPath: /mnt-rw
```
````

### E5 — stor-002-sec-057-ch-002 (retrieval rank 4)

Source: https://kubernetes.io/docs/concepts/storage/volumes/  
Heading: Volumes > Mount propagation > Caution:  
Original saved excerpt offsets: [0, 418)  
Snippet cut or saved source already truncated: False

```text
the [`mount(8)`](https://man7.org/linux/man-pages/man8/mount.8.html) Warning:`Bidirectional` mount propagation can be dangerous. It can damage the host operating system, and therefore, it is allowed only in privileged containers. Familiarity with Linux kernel behavior is strongly recommended. In addition, any volume mounts created by containers in Pods must be destroyed (unmounted) by the containers on termination.
```

### E6 — stor-002-sec-059-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/storage/volumes/  
Heading: Volumes > Read-only mounts > Recursive read-only mounts  
Original saved excerpt offsets: [32, 371)  
Snippet cut or saved source already truncated: True

```text
This is a stable feature in Kubernetes, and has been since version v1.33. It was first available in the v1.30 release. You can no longer disable or opt out of this feature or behavior (it is locked); if you explicitly set a value for the associated feature gate RecursiveReadOnlyMounts, Kubernetes ignores it but does not report any error.
```

---

## k8s-034

**Question:** When authoring Deployment, ReplicaSet, DaemonSet, StatefulSet, and Job manifests, how do their Pod selector requirements differ?

**No retriever passages were recorded for this question.** This does NOT establish that the question is unanswerable.

## k8s-039

**Question:** A Linux Pod uses `setHostnameAsFQDN: true` and stays in `Pending` / `ContainerCreating` with an event saying its FQDN is longer than 64 characters. What is causing the failure, and what preventive control does the documentation suggest?

### E1 — net-007-sec-012-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/  
Heading: DNS for Services and Pods > Pods > Pod's setHostnameAsFQDN field > Note:  
Original saved excerpt offsets: [223, 483)  
Snippet cut or saved source already truncated: False

```text
The Pod will remain in `Pending` status (`ContainerCreating` as seen by `kubectl`) generating
error events, such as Failed to construct FQDN from Pod hostname and cluster domain,
FQDN `long-FQDN` is too long (64 characters is the max, 70 characters requested).
```

### E2 — net-007-sec-012-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/  
Heading: DNS for Services and Pods > Pods > Pod's setHostnameAsFQDN field > Note:  
Original saved excerpt offsets: [12, 126)  
Snippet cut or saved source already truncated: False

```text
In Linux, the hostname field of the kernel (the `nodename` field of `struct utsname`) is limited to 64 characters.
```

### E3 — net-007-sec-011-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/  
Heading: DNS for Services and Pods > Pods > Pod's setHostnameAsFQDN field  
Original saved excerpt offsets: [407, 615)  
Snippet cut or saved source already truncated: False

```text
When you set `setHostnameAsFQDN: true` in the Pod spec, the kubelet writes the Pod's FQDN
into the hostname for that Pod's namespace. In this case, both `hostname` and `hostname --fqdn`
return the Pod's FQDN.
```

### E4 — net-007-sec-017-ch-001 (retrieval rank 4)

Source: https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/  
Heading: DNS for Services and Pods > DNS search domain list limits > Note:  
Original saved excerpt offsets: [12, 259)  
Snippet cut or saved source already truncated: False

```text
Some container runtimes of earlier versions may have their own restrictions on
the number of DNS search domains. Depending on the container runtime
environment, the pods with a large number of DNS search domains may get stuck in
the pending state.
```

### E5 — net-007-sec-011-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/  
Heading: DNS for Services and Pods > Pods > Pod's setHostnameAsFQDN field  
Original saved excerpt offsets: [35, 405)  
Snippet cut or saved source already truncated: False

```text
When a Pod is configured to have fully qualified domain name (FQDN), its
hostname is the short hostname. For example, if you have a Pod with the fully
qualified domain name `busybox-1.busybox-subdomain.my-namespace.svc.cluster-domain.example`,
then by default the `hostname` command inside that Pod returns `busybox-1` and the
`hostname --fqdn` command returns the FQDN.
```

### E6 — net-007-sec-009-ch-002 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/  
Heading: DNS for Services and Pods > Pods > Pod's hostname and subdomain fields  
Original saved excerpt offsets: [0, 186)  
Snippet cut or saved source already truncated: False

````text
labels:
    name: busybox
spec:
  hostname: busybox-2
  subdomain: busybox-subdomain
  containers:
  - image: busybox:1.28
    command:
      - sleep
      - "3600"
    name: busybox
```
````

---

## k8s-040

**Question:** An application needs dynamically provisioned persistent storage, must mount that storage into a Pod, and later needs a dynamically created snapshot of it. Which Kubernetes objects and fields connect those three steps?

### E1 — stor-007-sec-003-ch-001 (retrieval rank 4)

Source: https://kubernetes.io/docs/concepts/storage/dynamic-provisioning/  
Heading: Dynamic Volume Provisioning > Enabling Dynamic Provisioning  
Original saved excerpt offsets: [34, 475)  
Snippet cut or saved source already truncated: False

```text
To enable dynamic provisioning, a cluster administrator needs to pre-create
one or more StorageClass objects for users.
StorageClass objects define which provisioner should be used and what parameters
should be passed to that provisioner when dynamic provisioning is invoked.
The name of a StorageClass object must be a valid
[DNS subdomain name](https://kubernetes.io/docs/concepts/overview/working-with-objects/names/#dns-subdomain-names).
```

### E2 — stor-008-sec-006-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/storage/volume-snapshots/  
Heading: Volume Snapshots > Lifecycle of a volume snapshot and volume snapshot content > Provisioning Volume Snapshot > Dynamic  
Original saved excerpt offsets: [14, 315)  
Snippet cut or saved source already truncated: False

```text
Instead of using a pre-existing snapshot, you can request that a snapshot to be dynamically
taken from a PersistentVolumeClaim. The [VolumeSnapshotClass](https://kubernetes.io/docs/concepts/storage/volume-snapshot-classes/)
specifies storage provider-specific parameters to use when taking a snapshot.
```

### E3 — stor-007-sec-004-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/storage/dynamic-provisioning/  
Heading: Dynamic Volume Provisioning > Using Dynamic Provisioning  
Original saved excerpt offsets: [31, 139)  
Snippet cut or saved source already truncated: False

```text
Users request dynamically provisioned storage by including a storage class in
their `PersistentVolumeClaim`.
```

### E4 — stor-007-sec-001-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/storage/dynamic-provisioning/  
Heading: Dynamic Volume Provisioning  
Original saved excerpt offsets: [107, 396)  
Snippet cut or saved source already truncated: False

```text
Without dynamic provisioning, cluster administrators have to manually make
calls to their cloud or storage provider to create new storage volumes, and
then create [`PersistentVolume` objects](https://kubernetes.io/docs/concepts/storage/persistent-volumes/)
to represent them in Kubernetes.
```

### E5 — stor-007-sec-001-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/storage/dynamic-provisioning/  
Heading: Dynamic Volume Provisioning  
Original saved excerpt offsets: [503, 665)  
Snippet cut or saved source already truncated: False

```text
Instead, it
automatically provisions storage when users create
[`PersistentVolumeClaim` objects](https://kubernetes.io/docs/concepts/storage/persistent-volumes/).
```

### E6 — stor-007-sec-004-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/storage/dynamic-provisioning/  
Heading: Dynamic Volume Provisioning > Using Dynamic Provisioning  
Original saved excerpt offsets: [930, 1064)  
Snippet cut or saved source already truncated: False

```text
This claim results in an SSD-like Persistent Disk being automatically
provisioned. When the claim is deleted, the volume is destroyed.
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

## k8s-067

**Question:** What does the DNS A or AAAA record for a headless Service resolve to, and how does that differ from a normal Service?

### E1 — net-007-sec-005-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/  
Heading: DNS for Services and Pods > Services > A/AAAA records  
Original saved excerpt offsets: [20, 269)  
Snippet cut or saved source already truncated: False

```text
"Normal" (not headless) Services are assigned DNS A and/or AAAA records,
depending on the IP family or families of the Service, with a name of the form
`my-svc.my-namespace.svc.cluster-domain.example`. This resolves to the cluster IP
of the Service.
```

### E2 — net-007-sec-005-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/  
Heading: DNS for Services and Pods > Services > A/AAAA records  
Original saved excerpt offsets: [271, 713)  
Snippet cut or saved source already truncated: False

```text
[Headless Services](https://kubernetes.io/docs/concepts/services-networking/service/#headless-services)
(without a cluster IP) are also assigned DNS A and/or AAAA records,
with a name of the form `my-svc.my-namespace.svc.cluster-domain.example`. Unlike normal
Services, this resolves to the set of IPs of all of the Pods selected by the Service.
Clients are expected to consume the set or else use standard round-robin
selection from the set.
```

### E3 — net-002-sec-039-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/services-networking/service/  
Heading: Service > Headless Services > With selectors  
Original saved excerpt offsets: [20, 276)  
Snippet cut or saved source already truncated: False

```text
For headless Services that define selectors, the endpoints controller creates
EndpointSlices in the Kubernetes API, and modifies the DNS configuration to return
A or AAAA records (IPv4 or IPv6 addresses) that point directly to the Pods backing the Service.
```

### E4 — net-002-sec-040-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/services-networking/service/  
Heading: Service > Headless Services > Without selectors  
Original saved excerpt offsets: [190, 487)  
Snippet cut or saved source already truncated: False

```text
- DNS CNAME records for `type: ExternalName` Services.
- DNS A / AAAA records for all IP addresses of the Service's ready endpoints, for all Service types other than ExternalName .
- For IPv4 endpoints, the DNS system creates A records.
  - For IPv6 endpoints, the DNS system creates AAAA records.
```

### E5 — net-002-sec-038-ch-001 (retrieval rank 4)

Source: https://kubernetes.io/docs/concepts/services-networking/service/  
Heading: Service > Headless Services  
Original saved excerpt offsets: [629, 1031)  
Snippet cut or saved source already truncated: False

```text
Services that are headless don't
configure routes and packet forwarding using
[virtual IP addresses and proxies](https://kubernetes.io/docs/reference/networking/virtual-ips/); instead, headless Services report the
endpoint IP addresses of the individual pods via internal DNS records, served through the cluster's
[DNS service](https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/).
```

### E6 — net-002-sec-040-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/services-networking/service/  
Heading: Service > Headless Services > Without selectors  
Original saved excerpt offsets: [23, 188)  
Snippet cut or saved source already truncated: False

```text
For headless Services that do not define selectors, the control plane does
not create EndpointSlice objects. However, the DNS system looks for and configures
either:
```

---

## k8s-068

**Question:** How do out-of-tree CSI volume plugins differ from legacy in-tree volume plugins, and which advanced storage operations in the supplied documentation depend on CSI?

**No retriever passages were recorded for this question.** This does NOT establish that the question is unanswerable.

## k8s-071

**Question:** A Pod will not start because a referenced Secret cannot be fetched. What should you verify first, and where should you look for details while Kubernetes retries?

### E1 — conf-003-sec-027-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/configuration/secret/  
Heading: Secrets > Working with Secrets > Using a Secret  
Original saved excerpt offsets: [640, 920)  
Snippet cut or saved source already truncated: False

```text
If the Secret cannot be fetched (perhaps because it does not exist, or
due to a temporary lack of connection to the API server) the kubelet
periodically retries running that Pod. The kubelet also reports an Event
for that Pod, including details of the problem fetching the Secret.
```

### E2 — conf-003-sec-028-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/configuration/secret/  
Heading: Secrets > Working with Secrets > Using a Secret > Optional Secrets  
Original saved excerpt offsets: [478, 595)  
Snippet cut or saved source already truncated: False

```text
By default, Secrets are required. None of a Pod's containers will start until
all non-optional Secrets are available.
```

### E3 — conf-003-sec-002-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/configuration/secret/  
Heading: Secrets > Caution:  
Original saved excerpt offsets: [898, 1046)  
Snippet cut or saved source already truncated: False

```text
See [Information security for Secrets](https://kubernetes.io/docs/concepts/configuration/secret/#information-security-for-secrets) for more details.
```

### E4 — conf-003-sec-027-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/configuration/secret/  
Heading: Secrets > Working with Secrets > Using a Secret  
Original saved excerpt offsets: [437, 638)  
Snippet cut or saved source already truncated: False

```text
Secret volume sources are validated to ensure that the specified object
reference actually points to an object of type Secret. Therefore, a Secret
needs to be created before any Pods that depend on it.
```

### E5 — conf-003-sec-028-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/configuration/secret/  
Heading: Secrets > Working with Secrets > Using a Secret > Optional Secrets  
Original saved excerpt offsets: [23, 193)  
Snippet cut or saved source already truncated: False

```text
When you reference a Secret in a Pod, you can mark the Secret as *optional*,
such as in the following example. If an optional Secret doesn't exist,
Kubernetes ignores it.
```

### E6 — conf-003-sec-002-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/configuration/secret/  
Heading: Secrets > Caution:  
Original saved excerpt offsets: [15, 416)  
Snippet cut or saved source already truncated: False

```text
Kubernetes Secrets are, by default, stored unencrypted in the API server's underlying data store
(etcd). Anyone with API access can retrieve or modify a Secret, and so can anyone with access to etcd.
Additionally, anyone who is authorized to create a Pod in a namespace can use that access to read
any Secret in that namespace; this includes indirect access such as the ability to create a
Deployment.
```

---

## k8s-072

**Question:** Which factors does kubelet use to order end-user Pods for node-pressure eviction after node-level reclamation has failed?

### E1 — sched-007-sec-002-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/  
Heading: Node-pressure Eviction > Self healing behavior  
Original saved excerpt offsets: [26, 301)  
Snippet cut or saved source already truncated: False

```text
The kubelet attempts to [reclaim node-level resources](https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/#reclaim-node-resources)
before it terminates end-user pods. For example, it removes unused container
images when disk resources are starved.
```

### E2 — sched-007-sec-021-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/  
Heading: Node-pressure Eviction > Node conditions > Pod selection for kubelet eviction  
Original saved excerpt offsets: [40, 193)  
Snippet cut or saved source already truncated: False

```text
If the kubelet's attempts to reclaim node-level resources don't bring the eviction
signal below the threshold, the kubelet begins to evict end-user pods.
```

### E3 — sched-007-sec-017-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/  
Heading: Node-pressure Eviction > Node conditions > Reclaiming node level resources  
Original saved excerpt offsets: [37, 118)  
Snippet cut or saved source already truncated: False

```text
The kubelet tries to reclaim node-level resources before it evicts end-user pods.
```

### E4 — sched-007-sec-017-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/  
Heading: Node-pressure Eviction > Node conditions > Reclaiming node level resources  
Original saved excerpt offsets: [120, 249)  
Snippet cut or saved source already truncated: False

```text
When a `DiskPressure` node condition is reported, the kubelet reclaims node-level
resources based on the filesystems on the node.
```

### E5 — sched-007-sec-021-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/  
Heading: Node-pressure Eviction > Node conditions > Pod selection for kubelet eviction  
Original saved excerpt offsets: [195, 273)  
Snippet cut or saved source already truncated: False

```text
The kubelet uses the following parameters to determine the pod eviction order:
```

### E6 — sched-007-sec-022-ch-001 (retrieval rank 4)

Source: https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/  
Heading: Node-pressure Eviction > Node conditions > Pod selection for kubelet eviction > Note:  
Original saved excerpt offsets: [951, 1137)  
Snippet cut or saved source already truncated: False

```text
When the kubelet evicts pods in response to inode or process ID starvation, it uses
the Pods' relative priority to determine the eviction order, because inodes and PIDs have no
requests.
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

## k8s-076

**Question:** A DaemonSet was copied from a Job manifest and its Pod template still uses `restartPolicy: OnFailure`. Why is that invalid, and what value should the DaemonSet use?

### E1 — work-013-sec-024-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/workloads/controllers/job/  
Heading: Jobs > Handling Pod and container failures > Pod failure policy > Note:  
Original saved excerpt offsets: [67, 315)  
Snippet cut or saved source already truncated: False

```text
- if you want to use a .spec.podFailurePolicy field for a Job, you must also define that Job's pod template with .spec.restartPolicy set to Never .
- the Pod failure policy rules you specify under spec.podFailurePolicy.rules are evaluated in order.
```

### E2 — work-003-sec-015-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/  
Heading: Pod Lifecycle > How Pods handle problems with containers > Container restarts > Pod-level container restart policy  
Original saved excerpt offsets: [41, 168)  
Snippet cut or saved source already truncated: False

```text
The `spec` of a Pod has a `restartPolicy` field with possible values Always, OnFailure,
and Never. The default value is Always.
```

### E3 — work-013-sec-022-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/workloads/controllers/job/  
Heading: Jobs > Handling Pod and container failures > Pod failure policy  
Original saved excerpt offsets: [1433, 1496)  
Snippet cut or saved source already truncated: True

```text
Here is a manifest for a Job that defines a `podFailurePolicy`:
```

### E4 — work-013-sec-018-ch-002 (retrieval rank 4)

Source: https://kubernetes.io/docs/concepts/workloads/controllers/job/  
Heading: Jobs > Handling Pod and container failures  
Original saved excerpt offsets: [82, 263)  
Snippet cut or saved source already truncated: False

```text
Note that even if you specify `.spec.parallelism = 1` and `.spec.completions = 1` and
`.spec.template.spec.restartPolicy = "Never"`, the same program may
sometimes be started twice.
```

### E5 — work-013-sec-024-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/workloads/controllers/job/  
Heading: Jobs > Handling Pod and container failures > Pod failure policy > Note:  
Original saved excerpt offsets: [650, 858)  
Snippet cut or saved source already truncated: False

```text
When specified, it should match one the container or initContainer names in the Pod template.
- you may specify the action taken when a Pod failure policy is matched by spec.podFailurePolicy.rules[*].action .
```

### E6 — work-003-sec-015-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/  
Heading: Pod Lifecycle > How Pods handle problems with containers > Container restarts > Pod-level container restart policy  
Original saved excerpt offsets: [689, 841)  
Snippet cut or saved source already truncated: False

```text
For init containers that exit with an error, the kubelet restarts the init container if
the Pod level `restartPolicy` is either `OnFailure` or `Always`:
```

---

## k8s-077

**Question:** What cloud-specific information and lifecycle checks does the cloud-controller-manager's Node controller perform for Kubernetes Nodes?

### E1 — arch-007-sec-013-ch-001 (retrieval rank 4)

Source: https://kubernetes.io/docs/concepts/architecture/cloud-controller/  
Heading: Cloud Controller Manager > What's next  
Original saved excerpt offsets: [970, 1184)  
Snippet cut or saved source already truncated: False

```text
Implementations specific to cloud providers are outside the core of Kubernetes and implement the CloudProvider interface.
  - For more information about developing plugins, see Developing Cloud Controller Manager .
```

### E2 — arch-007-sec-005-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/architecture/cloud-controller/  
Heading: Cloud Controller Manager > Cloud controller manager functions > Node controller  
Original saved excerpt offsets: [21, 362)  
Snippet cut or saved source already truncated: False

```text
The node controller is responsible for updating [Node](https://kubernetes.io/docs/concepts/architecture/nodes/) objects
when new servers are created in your cloud infrastructure. The node controller obtains information about the
hosts running inside your tenancy with the cloud provider. The node controller performs the following functions:
```

### E3 — arch-007-sec-005-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/architecture/cloud-controller/  
Heading: Cloud Controller Manager > Cloud controller manager functions > Node controller  
Original saved excerpt offsets: [479, 660)  
Snippet cut or saved source already truncated: False

```text
Annotating and labelling the Node object with cloud-specific information, such as the region the node is deployed into and the resources (CPU, memory, etc) that it has available.
3.
```

### E4 — arch-002-sec-011-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/architecture/nodes/  
Heading: Nodes > Node controller  
Original saved excerpt offsets: [1207, 1398)  
Snippet cut or saved source already truncated: False

```text
By default, the node controller checks the state of each node every 5 seconds.
This period can be configured using the `--node-monitor-period` flag on the
`kube-controller-manager` component.
```

### E5 — arch-007-sec-001-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/architecture/cloud-controller/  
Heading: Cloud Controller Manager  
Original saved excerpt offsets: [228, 630)  
Snippet cut or saved source already truncated: False

```text
The cloud-controller-manager is a Kubernetes [control plane](https://kubernetes.io/docs/reference/glossary/?all=true#term-control-plane) component
that embeds cloud-specific control logic. The cloud controller manager lets you link your
cluster into your cloud provider's API, and separates out the components that interact
with that cloud platform from components that only interact with your cluster.
```

### E6 — arch-002-sec-011-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/architecture/nodes/  
Heading: Nodes > Node controller  
Original saved excerpt offsets: [347, 705)  
Snippet cut or saved source already truncated: False

```text
The second is keeping the node controller's internal list of nodes up to date with
the cloud provider's list of available machines. When running in a cloud
environment and whenever a node is unhealthy, the node controller asks the cloud
provider if the VM for that node is still available. If not, the node
controller deletes the node from its list of nodes.
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

## k8s-081

**Question:** Inside a Linux Pod, `hostname --fqdn` returns the full DNS name but `hostname` returns only the short name. How can you make `hostname` return the FQDN too, and what Linux limit can then prevent the Pod from starting?

### E1 — net-007-sec-011-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/  
Heading: DNS for Services and Pods > Pods > Pod's setHostnameAsFQDN field  
Original saved excerpt offsets: [35, 405)  
Snippet cut or saved source already truncated: False

```text
When a Pod is configured to have fully qualified domain name (FQDN), its
hostname is the short hostname. For example, if you have a Pod with the fully
qualified domain name `busybox-1.busybox-subdomain.my-namespace.svc.cluster-domain.example`,
then by default the `hostname` command inside that Pod returns `busybox-1` and the
`hostname --fqdn` command returns the FQDN.
```

### E2 — net-007-sec-009-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/  
Heading: DNS for Services and Pods > Pods > Pod's hostname and subdomain fields  
Original saved excerpt offsets: [938, 1143)  
Snippet cut or saved source already truncated: True

```text
If there exists a headless Service in the same namespace as the Pod, with
the same name as the subdomain, the cluster's DNS Server also returns A and/or AAAA
records for the Pod's fully qualified hostname.
```

### E3 — net-007-sec-011-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/  
Heading: DNS for Services and Pods > Pods > Pod's setHostnameAsFQDN field  
Original saved excerpt offsets: [407, 615)  
Snippet cut or saved source already truncated: False

```text
When you set `setHostnameAsFQDN: true` in the Pod spec, the kubelet writes the Pod's FQDN
into the hostname for that Pod's namespace. In this case, both `hostname` and `hostname --fqdn`
return the Pod's FQDN.
```

### E4 — net-007-sec-012-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/  
Heading: DNS for Services and Pods > Pods > Pod's setHostnameAsFQDN field > Note:  
Original saved excerpt offsets: [223, 483)  
Snippet cut or saved source already truncated: False

```text
The Pod will remain in `Pending` status (`ContainerCreating` as seen by `kubectl`) generating
error events, such as Failed to construct FQDN from Pod hostname and cluster domain,
FQDN `long-FQDN` is too long (64 characters is the max, 70 characters requested).
```

### E5 — net-007-sec-009-ch-002 (retrieval rank 4)

Source: https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/  
Heading: DNS for Services and Pods > Pods > Pod's hostname and subdomain fields  
Original saved excerpt offsets: [188, 561)  
Snippet cut or saved source already truncated: False

```text
Given the above Service `"busybox-subdomain"` and the Pods which set `spec.subdomain`
to `"busybox-subdomain"`, the first Pod will see its own FQDN as
`"busybox-1.busybox-subdomain.my-namespace.svc.cluster-domain.example"`. DNS serves
A and/or AAAA records at that name, pointing to the Pod's IP. Both Pods "`busybox1`" and
"`busybox2`" will have their own address records.
```

### E6 — net-007-sec-009-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/  
Heading: DNS for Services and Pods > Pods > Pod's hostname and subdomain fields  
Original saved excerpt offsets: [502, 936)  
Snippet cut or saved source already truncated: True

```text
The Pod spec also has an optional `subdomain` field which can be used to indicate
that the pod is part of sub-group of the namespace. For example, a Pod with `spec.hostname`
set to `"foo"`, and `spec.subdomain` set to `"bar"`, in namespace `"my-namespace"`, will
have its hostname set to `"foo"` and its fully qualified domain name (FQDN) set to
`"foo.bar.my-namespace.svc.cluster.local"` (once more, as observed from within
the Pod).
```

---

## k8s-082

**Question:** Which PersistentVolumeClaim field explicitly binds a claim to a particular PersistentVolume, and what happens if that PersistentVolume is already bound to another claim?

### E1 — stor-003-sec-045-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/storage/persistent-volumes/  
Heading: Persistent Volumes > PersistentVolumeClaims > Volume Name  
Original saved excerpt offsets: [17, 338)  
Snippet cut or saved source already truncated: False

```text
Claims can use the `volumeName` field to explicitly bind to a specific PersistentVolume. You can also leave
`volumeName` unset, indicating that you'd like Kubernetes to set up a new PersistentVolume
that matches the claim.
If the specified PV is already bound to another PVC, the binding will be stuck
in a pending state.
```

### E2 — stor-003-sec-007-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/storage/persistent-volumes/  
Heading: Persistent Volumes > Lifecycle of a volume and claim > Binding  
Original saved excerpt offsets: [525, 614)  
Snippet cut or saved source already truncated: False

```text
Once bound, PersistentVolumeClaim binds are exclusive,
regardless of how they were bound.
```

### E3 — stor-002-sec-036-ch-001 (retrieval rank 4)

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

### E4 — stor-003-sec-007-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/storage/persistent-volumes/  
Heading: Persistent Volumes > Lifecycle of a volume and claim > Binding  
Original saved excerpt offsets: [13, 188)  
Snippet cut or saved source already truncated: False

```text
A user creates, or in the case of dynamic provisioning, has already created,
a PersistentVolumeClaim with a specific amount of storage requested and with
certain access modes.
```

### E5 — stor-003-sec-017-ch-001 (retrieval rank 1)

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

### E6 — stor-003-sec-017-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/storage/persistent-volumes/  
Heading: Persistent Volumes > Lifecycle of a volume and claim > Reserving a PersistentVolume  
Original saved excerpt offsets: [1070, 1378)  
Snippet cut or saved source already truncated: True

```text
This method does not guarantee any binding privileges to the PersistentVolume.
If other PersistentVolumeClaims could use the PV that you specify, you first
need to reserve that storage volume. Specify the relevant PersistentVolumeClaim
in the `claimRef` field of the PV so that other PVCs can not bind to it.
```

---

## k8s-083

**Question:** How can an HTTP probe be reported as successful while the application logs a `connection reset by peer` or `broken pipe`, and how is that behavior different from a failing liveness probe or an unfinished startup probe?

### E1 — work-015-sec-021-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/configuration/liveness-readiness-startup-probes/  
Heading: Liveness, Readiness, and Startup Probes > Probe mechanism details > HTTP probes > Caution:  
Original saved excerpt offsets: [219, 631)  
Snippet cut or saved source already truncated: False

```text
If you probe an endpoint that returns a response body larger than **10KiB**,
the kubelet will still mark the probe as successful based on the status code,
but it will close the connection after reaching the 10KiB limit.
This abrupt closure can cause **connection reset by peer** or **broken pipe errors** to appear in your application's logs,
which can be difficult to distinguish from legitimate network issues.
```

### E2 — work-015-sec-004-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/configuration/liveness-readiness-startup-probes/  
Heading: Liveness, Readiness, and Startup Probes > Types of probe > Liveness probe  
Original saved excerpt offsets: [292, 696)  
Snippet cut or saved source already truncated: False

```text
If a container fails its liveness probe more times than the configured tolerance,
the kubelet restarts that container.
Liveness probes do not wait for readiness probes to succeed. If you want to
wait before executing a liveness probe, you can either define
`initialDelaySeconds` or use a [startup probe](https://kubernetes.io/docs/concepts/configuration/liveness-readiness-startup-probes/#startup-probe).
```

### E3 — work-015-sec-021-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/configuration/liveness-readiness-startup-probes/  
Heading: Liveness, Readiness, and Startup Probes > Probe mechanism details > HTTP probes > Caution:  
Original saved excerpt offsets: [15, 217)  
Snippet cut or saved source already truncated: False

```text
When processing an `httpGet` probe, the kubelet stops reading the response body after 10KiB.
The probe's success is determined solely by the response status code, which is found in the response headers.
```

### E4 — work-015-sec-010-ch-001 (retrieval rank 4)

Source: https://kubernetes.io/docs/concepts/configuration/liveness-readiness-startup-probes/  
Heading: Liveness, Readiness, and Startup Probes > When to use each probe > When should you use a liveness probe?  
Original saved excerpt offsets: [473, 715)  
Snippet cut or saved source already truncated: False

```text
A common pattern for liveness probes is to use the same low-cost HTTP endpoint
as for readiness probes, but with a higher `failureThreshold`. This ensures
that the pod is observed as not-ready for some period of time before it is hard
killed.
```

### E5 — work-015-sec-005-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/configuration/liveness-readiness-startup-probes/  
Heading: Liveness, Readiness, and Startup Probes > Types of probe > Liveness probe > Caution:  
Original saved excerpt offsets: [15, 267)  
Snippet cut or saved source already truncated: False

```text
Liveness probes can be a powerful way to recover from application failures,
but they should be used with caution.
Liveness probes must be configured carefully to ensure that they truly indicate
unrecoverable application failure, for example a deadlock.
```

### E6 — work-015-sec-005-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/configuration/liveness-readiness-startup-probes/  
Heading: Liveness, Readiness, and Startup Probes > Types of probe > Liveness probe > Caution:  
Original saved excerpt offsets: [269, 633)  
Snippet cut or saved source already truncated: False

```text
Incorrect implementation of liveness probes can lead to cascading failures.
This results in restarting of container under high load; failed client requests
as your application became less scalable; and increased workload on remaining
pods due to some failed pods. Understand the difference between liveness and
readiness probes and when to apply them for your app.
```

---

## k8s-084

**Question:** In a cloud-hosted Kubernetes cluster, Pods on different nodes cannot communicate because the cloud network routes are not being configured. Which cloud-controller-manager function should you investigate, and where does that controller run?

### E1 — arch-007-sec-006-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/architecture/cloud-controller/  
Heading: Cloud Controller Manager > Cloud controller manager functions > Route controller  
Original saved excerpt offsets: [22, 205)  
Snippet cut or saved source already truncated: False

```text
The route controller is responsible for configuring routes in the cloud
appropriately so that containers on different nodes in your Kubernetes
cluster can communicate with each other.
```

### E2 — arch-007-sec-001-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/architecture/cloud-controller/  
Heading: Cloud Controller Manager  
Original saved excerpt offsets: [632, 876)  
Snippet cut or saved source already truncated: False

```text
By decoupling the interoperability logic between Kubernetes and the underlying cloud
infrastructure, the cloud-controller-manager component enables cloud providers to release
features at a different pace compared to the main Kubernetes project.
```

### E3 — arch-007-sec-001-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/architecture/cloud-controller/  
Heading: Cloud Controller Manager  
Original saved excerpt offsets: [878, 1029)  
Snippet cut or saved source already truncated: False

```text
The cloud-controller-manager is structured using a plugin
mechanism that allows different cloud providers to integrate their platforms with Kubernetes.
```

### E4 — arch-007-sec-006-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/architecture/cloud-controller/  
Heading: Cloud Controller Manager > Cloud controller manager functions > Route controller  
Original saved excerpt offsets: [207, 324)  
Snippet cut or saved source already truncated: False

```text
Depending on the cloud provider, the route controller might also allocate blocks
of IP addresses for the Pod network.
```

### E5 — arch-007-sec-002-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/architecture/cloud-controller/  
Heading: Cloud Controller Manager > Design  
Original saved excerpt offsets: [43, 318)  
Snippet cut or saved source already truncated: False

```text
The cloud controller manager runs in the control plane as a replicated set of processes
(usually, these are containers in Pods). Each cloud-controller-manager implements
multiple [controllers](https://kubernetes.io/docs/concepts/architecture/controller/) in a single
process.
```

### E6 — arch-007-sec-013-ch-001 (retrieval rank 4)

Source: https://kubernetes.io/docs/concepts/architecture/cloud-controller/  
Heading: Cloud Controller Manager > What's next  
Original saved excerpt offsets: [16, 465)  
Snippet cut or saved source already truncated: True

```text
- [Cloud Controller Manager Administration](https://kubernetes.io/docs/tasks/administer-cluster/running-cloud-controller/#cloud-controller-manager) has instructions on running and managing the cloud controller manager.
- To upgrade a HA control plane to use the cloud controller manager, see [Migrate Replicated Control Plane To Use Cloud Controller Manager](https://kubernetes.io/docs/tasks/administer-cluster/controller-manager-leader-migration/).
```

---

## k8s-086

**Question:** A Pod has `requiredDuringSchedulingIgnoredDuringExecution` inter-Pod affinity to Pods labeled `security=S1` in the same zone, but no matching Pod exists in the candidate zone. Why can the Pod remain unschedulable, and how would using the preferred form change the rule?

### E1 — sched-003-sec-019-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/  
Heading: Assigning Pods to Nodes > Affinity and anti-affinity > Inter-pod affinity and anti-affinity > Pod Affinity Example  
Original saved excerpt offsets: [814, 1072)  
Snippet cut or saved source already truncated: True

```text
This example defines one Pod affinity rule and one Pod anti-affinity rule. The
Pod affinity rule uses the "hard"
`requiredDuringSchedulingIgnoredDuringExecution`, while the anti-affinity rule
uses the "soft" `preferredDuringSchedulingIgnoredDuringExecution`.
```

### E2 — sched-003-sec-019-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/  
Heading: Assigning Pods to Nodes > Affinity and anti-affinity > Inter-pod affinity and anti-affinity > Pod Affinity Example  
Original saved excerpt offsets: [1074, 1520)  
Snippet cut or saved source already truncated: True

```text
The affinity rule specifies that the scheduler is allowed to place the example Pod
on a node only if that node belongs to a specific [zone](https://kubernetes.io/docs/concepts/scheduling-eviction/topology-spread-constraints/)
where other Pods have been labeled with `security=S1`.
For instance, if we have a cluster with a designated zone, let's call it "Zone V,"
consisting of nodes labeled with `topology.kubernetes.io/zone= [TRUNCATED EXCERPT]
```

### E3 — sched-003-sec-017-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/  
Heading: Assigning Pods to Nodes > Affinity and anti-affinity > Inter-pod affinity and anti-affinity > Scheduling Behavior  
Original saved excerpt offsets: [176, 485)  
Snippet cut or saved source already truncated: False

```text
Hard Constraints (Node Filtering):
- podAffinity.requiredDuringSchedulingIgnoredDuringExecution and podAntiAffinity.requiredDuringSchedulingIgnoredDuringExecution :
- The scheduler ensures the new Pod is assigned to nodes that satisfy these required affinity and anti-affinity rules based on existing Pods.
2.
```

### E4 — sched-003-sec-017-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/  
Heading: Assigning Pods to Nodes > Affinity and anti-affinity > Inter-pod affinity and anti-affinity > Scheduling Behavior  
Original saved excerpt offsets: [486, 781)  
Snippet cut or saved source already truncated: False

```text
Soft Constraints (Scoring):
- podAffinity.preferredDuringSchedulingIgnoredDuringExecution and podAntiAffinity.preferredDuringSchedulingIgnoredDuringExecution :
- The scheduler scores nodes based on how well they meet these preferred affinity and anti-affinity rules to optimize Pod placement.
3.
```

### E5 — sched-003-sec-019-ch-002 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/  
Heading: Assigning Pods to Nodes > Affinity and anti-affinity > Inter-pod affinity and anti-affinity > Pod Affinity Example  
Original saved excerpt offsets: [864, 985)  
Snippet cut or saved source already truncated: True

```text
Conversely, the anti-affinity rule does not impact
scheduling into Zone R if there are no Pods with `security=S2` labels.
```

### E6 — sched-003-sec-019-ch-002 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/  
Heading: Assigning Pods to Nodes > Affinity and anti-affinity > Inter-pod affinity and anti-affinity > Pod Affinity Example  
Original saved excerpt offsets: [0, 270)  
Snippet cut or saved source already truncated: True

```text
assign the Pod to any node within Zone V, as long as there is at least one Pod within
Zone V already labeled with `security=S1`. Conversely, if there are no Pods with `security=S1`
labels in Zone V, the scheduler will not assign the example Pod to any node in that zone.
```

---

## k8s-087

**Question:** What `default` ServiceAccount does Kubernetes create in each namespace, what permissions does it have by default under RBAC, and what happens if it is deleted?

### E1 — sec-004-sec-003-ch-001 (retrieval rank 1)

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

### E2 — sec-004-sec-003-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/security/service-accounts/  
Heading: Service Accounts > What are service accounts? > Default service accounts  
Original saved excerpt offsets: [30, 166)  
Snippet cut or saved source already truncated: False

```text
When you create a cluster, Kubernetes automatically creates a ServiceAccount
object named `default` for every namespace in your cluster.
```

### E3 — sec-004-sec-006-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/security/service-accounts/  
Heading: Service Accounts > How to use service accounts > Grant permissions to a ServiceAccount  
Original saved excerpt offsets: [43, 253)  
Snippet cut or saved source already truncated: False

```text
You can use the built-in Kubernetes
[role-based access control (RBAC)](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)
mechanism to grant the minimum permissions required by each service account.
```

### E4 — sec-004-sec-006-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/security/service-accounts/  
Heading: Service Accounts > How to use service accounts > Grant permissions to a ServiceAccount  
Original saved excerpt offsets: [345, 475)  
Snippet cut or saved source already truncated: False

```text
RBAC lets you define a minimum set of permissions so that the
service account permissions follow the principle of least privilege.
```

### E5 — sec-004-sec-005-ch-001 (retrieval rank 4)

Source: https://kubernetes.io/docs/concepts/security/service-accounts/  
Heading: Service Accounts > How to use service accounts  
Original saved excerpt offsets: [209, 370)  
Snippet cut or saved source already truncated: False

```text
Grant permissions to the ServiceAccount object using an authorization mechanism such as [RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/).
3.
```

### E6 — sec-004-sec-002-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/security/service-accounts/  
Heading: Service Accounts > What are service accounts?  
Original saved excerpt offsets: [733, 982)  
Snippet cut or saved source already truncated: True

```text
Every namespace gets a [`default` ServiceAccount](https://kubernetes.io/docs/concepts/security/service-accounts/#default-service-accounts) upon creation.
- **Lightweight:** Service accounts exist in the cluster and are defined in the Kubernetes API.
```

---

## k8s-088

**Question:** How does a Kubernetes Service differ from EndpointSlices in representing a changing set of backends, and why can the same endpoint temporarily appear in more than one EndpointSlice?

### E1 — net-005-sec-012-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/services-networking/endpoint-slices/  
Heading: EndpointSlices > EndpointSlice API > Duplicate endpoints  
Original saved excerpt offsets: [25, 284)  
Snippet cut or saved source already truncated: False

```text
Due to the nature of EndpointSlice changes, endpoints may be represented in more
than one EndpointSlice at the same time. This naturally occurs as changes to
different EndpointSlice objects can arrive at the Kubernetes client watch / cache
at different times.
```

### E2 — net-005-sec-011-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/services-networking/endpoint-slices/  
Heading: EndpointSlices > EndpointSlice API > Distribution of EndpointSlices  
Original saved excerpt offsets: [36, 277)  
Snippet cut or saved source already truncated: True

```text
Each EndpointSlice has a set of ports that applies to all endpoints within the
resource. When named ports are used for a Service, Pods may end up with
different target port numbers for the same named port, requiring different
EndpointSlices.
```

### E3 — net-005-sec-011-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/services-networking/endpoint-slices/  
Heading: EndpointSlices > EndpointSlice API > Distribution of EndpointSlices  
Original saved excerpt offsets: [806, 1236)  
Snippet cut or saved source already truncated: True

```text
Importantly, the third step prioritizes limiting EndpointSlice updates over a
perfectly full distribution of EndpointSlices. As an example, if there are 10
new endpoints to add and 2 EndpointSlices with room for 5 more endpoints each,
this approach will create a new EndpointSlice instead of filling up the 2
existing EndpointSlices. In other words, a single EndpointSlice creation is
preferable to multiple EndpointSlice updates.
```

### E4 — net-005-sec-002-ch-001 (retrieval rank 4)

Source: https://kubernetes.io/docs/concepts/services-networking/endpoint-slices/  
Heading: EndpointSlices > EndpointSlice API  
Original saved excerpt offsets: [1139, 1453)  
Snippet cut or saved source already truncated: True

```text
By default, the control plane creates and manages EndpointSlices to have no
more than 100 endpoints each. You can configure this with the
`--max-endpoints-per-slice`
[kube-controller-manager](https://kubernetes.io/docs/reference/command-line-tools-reference/kube-controller-manager/)
flag, up to a maximum of 1000.
```

### E5 — net-002-sec-012-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/services-networking/service/  
Heading: Service > Defining a Service > EndpointSlices  
Original saved excerpt offsets: [20, 206)  
Snippet cut or saved source already truncated: False

```text
[EndpointSlices](https://kubernetes.io/docs/concepts/services-networking/endpoint-slices/) are objects that
represent a subset (a *slice*) of the backing network endpoints for a Service.
```

### E6 — net-002-sec-012-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/services-networking/service/  
Heading: Service > Defining a Service > EndpointSlices  
Original saved excerpt offsets: [664, 795)  
Snippet cut or saved source already truncated: False

```text
See [EndpointSlices](https://kubernetes.io/docs/concepts/services-networking/endpoint-slices/) for more
information about this API.
```

---

## k8s-089

**Question:** A StorageClass uses `WaitForFirstConsumer`, but its Pod sets `spec.nodeName` and the PVC remains Pending. Why does that happen, and how should the Pod express the same node preference instead?

### E1 — stor-006-sec-011-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/storage/storage-classes/  
Heading: Storage Classes > Volume binding mode > Note:  
Original saved excerpt offsets: [12, 227)  
Snippet cut or saved source already truncated: False

```text
If you choose to use `WaitForFirstConsumer`, do not use `nodeName` in the Pod spec
to specify node affinity.
If `nodeName` is used in this case, the scheduler will be bypassed and PVC will remain in `pending` state.
```

### E2 — stor-005-sec-007-ch-001 (retrieval rank 4)

Source: https://kubernetes.io/docs/concepts/storage/ephemeral-volumes/  
Heading: Ephemeral Volumes > Lifecycle and PersistentVolumeClaim  
Original saved excerpt offsets: [574, 854)  
Snippet cut or saved source already truncated: True

```text
That triggers volume binding and/or provisioning, either immediately if
the [StorageClass](https://kubernetes.io/docs/concepts/storage/storage-classes) uses immediate volume binding or when the Pod is
tentatively scheduled onto a node (`WaitForFirstConsumer` volume
binding mode).
```

### E3 — stor-006-sec-004-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/storage/storage-classes/  
Heading: Storage Classes > Default StorageClass > Note:  
Original saved excerpt offsets: [12, 324)  
Snippet cut or saved source already truncated: False

```text
You can create a PersistentVolumeClaim without specifying a `storageClassName`
for the new PVC, and you can do so even when no default StorageClass exists
in your cluster. In this case, the new PVC creates as you defined it, and the
`storageClassName` of that PVC remains unset until a default becomes available.
```

### E4 — stor-003-sec-049-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/storage/persistent-volumes/  
Heading: Persistent Volumes > PersistentVolumeClaims > Class  
Original saved excerpt offsets: [11, 302)  
Snippet cut or saved source already truncated: True

```text
A claim can request a particular class by specifying the name of a
[StorageClass](https://kubernetes.io/docs/concepts/storage/storage-classes/)
using the attribute `storageClassName`.
Only PVs of the requested class, ones with the same `storageClassName` as the PVC,
can be bound to the PVC.
```

### E5 — stor-003-sec-049-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/storage/persistent-volumes/  
Heading: Persistent Volumes > PersistentVolumeClaims > Class  
Original saved excerpt offsets: [550, 827)  
Snippet cut or saved source already truncated: True

```text
A PVC with no `storageClassName` is not quite the same and is treated differently
by the cluster, depending on whether the
[`DefaultStorageClass` admission plugin](https://kubernetes.io/docs/reference/access-authn-authz/admission-controllers/#defaultstorageclass)
is turned on.
```

### E6 — stor-006-sec-004-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/storage/storage-classes/  
Heading: Storage Classes > Default StorageClass > Note:  
Original saved excerpt offsets: [913, 1056)  
Snippet cut or saved source already truncated: False

```text
If you have an existing PVC where the `storageClassName` is `""`, and you configure
a default StorageClass, then this PVC will not get updated.
```

---

## k8s-090

**Question:** A three-replica Deployment manifest uses `RollingUpdate` with `maxSurge: 1` and `maxUnavailable: 1`. After a bad release, which rollout settings are present in the manifest, and what event in the supplied Deployment history confirms that Kubernetes rolled the Deployment back?

### E1 — work-009-sec-038-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/workloads/controllers/deployment/  
Heading: Deployments > Writing a Deployment Spec > Strategy > Rolling Update Deployment  
Original saved excerpt offsets: [32, 285)  
Snippet cut or saved source already truncated: False

```text
The Deployment updates Pods in a rolling update
fashion (gradually scale down the old ReplicaSets and scale up the new one) when `.spec.strategy.type==RollingUpdate`. You can specify `maxUnavailable` and `maxSurge` to control
the rolling update process.
```

### E2 — work-009-sec-014-ch-002 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/workloads/controllers/deployment/  
Heading: Deployments > Rolling Back a Deployment > Note:  
Original saved excerpt offsets: [0, 139)  
Snippet cut or saved source already truncated: True

```text
mng 0/1 ImagePullBackOff 0 6s` Note:The Deployment controller stops the bad rollout automatically, and stops scaling up the new ReplicaSet.
```

### E3 — work-009-sec-014-ch-002 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/workloads/controllers/deployment/  
Heading: Deployments > Rolling Back a Deployment > Note:  
Original saved excerpt offsets: [242, 691)  
Snippet cut or saved source already truncated: True

```text
Kubernetes by default sets the value to 25%.
- Get the description of the Deployment: `kubectl describe deployment` The output is similar to this: `Name: nginx-deployment Namespace: default CreationTimestamp: Tue, 15 Mar 2016 14:48:04 -0700 Labels: app=nginx Selector: app=nginx Replicas: 3 desired | 1 updated | 4 total | 3 available | 1 unavailable StrategyType: RollingUpdate MinReadySeconds: 0 RollingUpdateStrategy: 25% max unavailable, 25% max
```

### E4 — work-009-sec-015-ch-001 (retrieval rank 4)

Source: https://kubernetes.io/docs/concepts/workloads/controllers/deployment/  
Heading: Deployments > Rolling Back a Deployment > Checking Rollout History of a Deployment  
Original saved excerpt offsets: [632, 939)  
Snippet cut or saved source already truncated: False

```text
This flag is deprecated and will be removed in a future release.
- Annotating the Deployment with kubectl annotate deployment/nginx-deployment kubernetes.io/change-cause="image updated to 1.16.1"
  - Manually editing the manifest of the resource.
  - Using tooling that sets the annotation automatically.
2.
```

### E5 — work-009-sec-015-ch-001 (retrieval rank 4)

Source: https://kubernetes.io/docs/concepts/workloads/controllers/deployment/  
Heading: Deployments > Rolling Back a Deployment > Checking Rollout History of a Deployment  
Original saved excerpt offsets: [109, 439)  
Snippet cut or saved source already truncated: False

```text
First, check the revisions of this Deployment: `kubectl rollout history deployment/nginx-deployment` The output is similar to this: `deployments "nginx-deployment" REVISION CHANGE-CAUSE 1 <none> 2 <none> 3 <none>` `CHANGE-CAUSE` is copied from the Deployment annotation `kubernetes.io/change-cause` to its revisions upon creation.
```

### E6 — work-009-sec-014-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/workloads/controllers/deployment/  
Heading: Deployments > Rolling Back a Deployment > Note:  
Original saved excerpt offsets: [12, 317)  
Snippet cut or saved source already truncated: True

```text
- Suppose that you made a typo while updating the Deployment, by putting the image name as `nginx:1.161` instead of `nginx:1.16.1`: `kubectl set image deployment/nginx-deployment nginx = nginx:1.161` The output is similar to this: `deployment.apps/nginx-deployment image updated`
- The rollout gets stuck.
```

---

## k8s-091

**Question:** After enabling Konnectivity, control-plane requests to kubelets, Pods, and Services stop reaching nodes. Which Konnectivity components and connection direction should you check, and how is this architecture different from the older SSH-tunnel approach?

### E1 — arch-003-sec-008-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/architecture/control-plane-node-communication/  
Heading: Communication between Nodes and the Control Plane > Control plane to node > Konnectivity service  
Original saved excerpt offsets: [422, 529)  
Snippet cut or saved source already truncated: False

```text
After enabling the Konnectivity service, all control plane to nodes traffic goes through these
connections.
```

### E2 — arch-003-sec-002-ch-001 (retrieval rank 4)

Source: https://kubernetes.io/docs/concepts/architecture/control-plane-node-communication/  
Heading: Communication between Nodes and the Control Plane > Node to Control Plane  
Original saved excerpt offsets: [150, 232)  
Snippet cut or saved source already truncated: True

```text
None of the other control plane components are designed to expose
remote services.
```

### E3 — arch-003-sec-009-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/architecture/control-plane-node-communication/  
Heading: Communication between Nodes and the Control Plane > What's next  
Original saved excerpt offsets: [16, 328)  
Snippet cut or saved source already truncated: False

```text
- Read about the Kubernetes control plane components
- Learn more about Hubs and Spoke model
- Learn how to Secure a Cluster
- Learn more about the Kubernetes API
- Set up Konnectivity service
- Use Port Forwarding to Access Applications in a Cluster
- Learn how to Fetch logs for Pods , use kubectl port-forward
```

### E4 — arch-003-sec-008-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/architecture/control-plane-node-communication/  
Heading: Communication between Nodes and the Control Plane > Control plane to node > Konnectivity service  
Original saved excerpt offsets: [26, 160)  
Snippet cut or saved source already truncated: False

```text
As a replacement to the SSH tunnels, the Konnectivity service provides TCP level proxy for the
control plane to cluster communication.
```

### E5 — arch-003-sec-006-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/architecture/control-plane-node-communication/  
Heading: Communication between Nodes and the Control Plane > Control plane to node > SSH tunnels  
Original saved excerpt offsets: [17, 152)  
Snippet cut or saved source already truncated: False

```text
Kubernetes supports [SSH tunnels](https://www.ssh.com/academy/ssh/tunneling) to protect the control plane to nodes communication paths.
```

### E6 — arch-003-sec-006-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/architecture/control-plane-node-communication/  
Heading: Communication between Nodes and the Control Plane > Control plane to node > SSH tunnels  
Original saved excerpt offsets: [153, 383)  
Snippet cut or saved source already truncated: False

```text
In this
configuration, the API server initiates an SSH tunnel to each node in the cluster (connecting to
the SSH server listening on port 22) and passes all traffic destined for a kubelet, node, pod, or
service through the tunnel.
```

---

## k8s-092

**Question:** A container has restarted repeatedly and `kubectl describe pod` reports `Reason: OOMKilled`. What does that indicate, and what resource change should you consider if the application is otherwise behaving as expected?

### E1 — conf-004-sec-041-ch-002 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/  
Heading: Resource Management for Pods and Containers > Troubleshooting > My container is terminated  
Original saved excerpt offsets: [439, 654)  
Snippet cut or saved source already truncated: False

```text
Your next step might be to check the application code for a memory leak. If you
find that the application is behaving how you expect, consider setting a higher
memory limit (and possibly request) for that container.
```

### E2 — conf-004-sec-041-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/  
Heading: Resource Management for Pods and Containers > Troubleshooting > My container is terminated  
Original saved excerpt offsets: [32, 236)  
Snippet cut or saved source already truncated: True

```text
Your container might get terminated because it is resource-starved. To check
whether a container is being killed because it is hitting a resource limit, call
`kubectl describe pod` on the Pod of interest:
```

### E3 — conf-004-sec-041-ch-002 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/  
Heading: Resource Management for Pods and Containers > Troubleshooting > My container is terminated  
Original saved excerpt offsets: [197, 437)  
Snippet cut or saved source already truncated: False

```text
In the preceding example, the `Restart Count: 5` indicates that the `simmemleak`
container in the Pod was terminated and restarted five times (so far).
The `OOMKilled` reason shows that the container tried to use more memory than its limit.
```

### E4 — work-004-sec-011-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/workloads/pods/init-containers/  
Heading: Init Containers > Detailed behavior > Pod restart reasons  
Original saved excerpt offsets: [113, 423)  
Snippet cut or saved source already truncated: False

```text
- The Pod infrastructure container is restarted. This is uncommon and would have to be done by someone with root access to nodes.
- All containers in a Pod are terminated while restartPolicy is set to Always, forcing a restart, and the init container completion record has been lost due to garbage collection .
```

### E5 — work-004-sec-011-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/workloads/pods/init-containers/  
Heading: Init Containers > Detailed behavior > Pod restart reasons  
Original saved excerpt offsets: [425, 730)  
Snippet cut or saved source already truncated: False

```text
The Pod will not be restarted when the init container image is changed, or the
init container completion record has been lost due to garbage collection. This
applies for Kubernetes v1.20 and later. If you are using an earlier version of
Kubernetes, consult the documentation for the version you are using.
```

### E6 — work-003-sec-012-ch-001 (retrieval rank 4)

Source: https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/  
Heading: Pod Lifecycle > How Pods handle problems with containers  
Original saved excerpt offsets: [691, 871)  
Snippet cut or saved source already truncated: True

```text
CrashLoopBackOff state : This indicates that the backoff delay mechanism is currently in effect for a given container that is in a crash loop, failing and restarting repeatedly.
4.
```

---

## k8s-093

**Question:** A high-priority pending Pod satisfies its `nodeSelector` and required node-affinity rules only on Node N, but it also has inter-Pod affinity to a lower-priority Pod currently running on N. Why might preempting that lower-priority Pod fail to make Node N usable, even though the pending Pod has higher priority?

### E1 — sched-006-sec-021-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/scheduling-eviction/pod-priority-preemption/  
Heading: Pod Priority and Preemption > Preemption > Limitations of preemption > Note:  
Original saved excerpt offsets: [12, 302)  
Snippet cut or saved source already truncated: False

```text
If a pending Pod has inter-pod [affinity](https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/#affinity-and-anti-affinity)
to one or more of the lower-priority Pods on the Node, the inter-Pod affinity
rule cannot be satisfied in the absence of those lower-priority Pods.
```

### E2 — sched-006-sec-022-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/scheduling-eviction/pod-priority-preemption/  
Heading: Pod Priority and Preemption > Preemption > Limitations of preemption > Cross node preemption  
Original saved excerpt offsets: [220, 669)  
Snippet cut or saved source already truncated: False

```text
- Pod P is being considered for Node N.
- Pod Q is running on another Node in the same Zone as Node N.
- Pod P has Zone-wide anti-affinity with Pod Q ( topologyKey: topology.kubernetes.io/zone ).
- There are no other cases of anti-affinity between Pod P and other Pods in the Zone.
- In order to schedule Pod P on Node N, Pod Q can be preempted, but scheduler does not perform cross-node preemption. So, Pod P will be deemed unschedulable on Node N.
```

### E3 — sched-006-sec-021-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/scheduling-eviction/pod-priority-preemption/  
Heading: Pod Priority and Preemption > Preemption > Limitations of preemption > Note:  
Original saved excerpt offsets: [526, 643)  
Snippet cut or saved source already truncated: False

```text
Our recommended solution for this problem is to create inter-Pod affinity only
towards equal or higher priority Pods.
```

### E4 — sched-006-sec-028-ch-001 (retrieval rank 4)

Source: https://kubernetes.io/docs/concepts/scheduling-eviction/pod-priority-preemption/  
Heading: Pod Priority and Preemption > Troubleshooting > Higher priority Pods are preempted before lower priority pods  
Original saved excerpt offsets: [129, 270)  
Snippet cut or saved source already truncated: False

```text
If no node is
found, the scheduler tries to remove Pods with lower priority from an arbitrary
node in order to make room for the pending pod.
```

### E5 — sched-006-sec-020-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/scheduling-eviction/pod-priority-preemption/  
Heading: Pod Priority and Preemption > Preemption > Limitations of preemption > Inter-Pod affinity on lower-priority Pods  
Original saved excerpt offsets: [48, 261)  
Snippet cut or saved source already truncated: False

```text
A Node is considered for preemption only when the answer to this question is
yes: "If all the Pods with lower priority than the pending Pod are removed from
the Node, can the pending Pod be scheduled on the Node?"
```

### E6 — sched-006-sec-022-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/scheduling-eviction/pod-priority-preemption/  
Heading: Pod Priority and Preemption > Preemption > Limitations of preemption > Cross node preemption  
Original saved excerpt offsets: [28, 218)  
Snippet cut or saved source already truncated: False

```text
Suppose a Node N is being considered for preemption so that a pending Pod P can
be scheduled on N. P might become feasible on N only if a Pod on another Node is
preempted. Here's an example:
```

---

## k8s-094

**Question:** You are designing RBAC for an application team that can create ordinary workloads but should not be able to gain host-level access. Why is granting arbitrary PersistentVolume creation especially dangerous, and what permissions should remain tightly restricted?

### E1 — sec-006-sec-010-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/security/rbac-good-practices/  
Heading: Role Based Access Control Good Practices > Kubernetes RBAC - privilege escalation risks > Persistent volume creation  
Original saved excerpt offsets: [32, 321)  
Snippet cut or saved source already truncated: False

```text
If someone - or some application - is allowed to create arbitrary PersistentVolumes, that access
includes the creation of `hostPath` volumes, which then means that a Pod would get access
to the underlying host filesystem(s) on the associated node. Granting that ability is a security risk.
```

### E2 — sec-006-sec-009-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/security/rbac-good-practices/  
Heading: Role Based Access Control Good Practices > Kubernetes RBAC - privilege escalation risks > Workload creation  
Original saved excerpt offsets: [333, 598)  
Snippet cut or saved source already truncated: False

```text
Additionally, since Pods can run as any
[ServiceAccount](https://kubernetes.io/docs/reference/access-authn-authz/service-accounts-admin/), granting permission
to create workloads also implicitly grants the API access levels of any service account in that
namespace.
```

### E3 — sec-006-sec-009-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/security/rbac-good-practices/  
Heading: Role Based Access Control Good Practices > Kubernetes RBAC - privilege escalation risks > Workload creation  
Original saved excerpt offsets: [23, 332)  
Snippet cut or saved source already truncated: False

```text
Permission to create workloads (either Pods, or
[workload resources](https://kubernetes.io/docs/concepts/workloads/controllers/) that manage Pods) in a namespace
implicitly grants access to many other resources in that namespace, such as Secrets, ConfigMaps, and
PersistentVolumes that can be mounted in Pods.
```

### E4 — sec-006-sec-010-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/security/rbac-good-practices/  
Heading: Role Based Access Control Good Practices > Kubernetes RBAC - privilege escalation risks > Persistent volume creation  
Original saved excerpt offsets: [540, 608)  
Snippet cut or saved source already truncated: False

```text
You should only allow access to create PersistentVolume objects for:
```

### E5 — sec-006-sec-020-ch-001 (retrieval rank 4)

Source: https://kubernetes.io/docs/concepts/security/rbac-good-practices/  
Heading: Role Based Access Control Good Practices > Kubernetes RBAC - denial of service risks > Object creation denial-of-service  
Original saved excerpt offsets: [39, 486)  
Snippet cut or saved source already truncated: False

```text
Users who have rights to create objects in a cluster may be able to create sufficient large
objects to create a denial of service condition either based on the size or number of objects, as discussed in
[etcd used by Kubernetes is vulnerable to OOM attack](https://github.com/kubernetes/kubernetes/issues/107325). This may be
specifically relevant in multi-tenant clusters if semi-trusted or untrusted users
are allowed limited access to a system.
```

### E6 — sec-006-sec-003-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/security/rbac-good-practices/  
Heading: Role Based Access Control Good Practices > General good practice > Least privilege  
Original saved excerpt offsets: [257, 316)  
Snippet cut or saved source already truncated: False

```text
- Assign permissions at the namespace level where possible.
```

---

## k8s-095

**Question:** Backend Pods are frequently replaced and their IP addresses change. Why should a frontend avoid tracking those Pod IPs directly, and how do the Kubernetes network model and Service abstraction allow the frontend to keep reaching the backend?

### E1 — net-001-sec-002-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/services-networking/  
Heading: Services, Load Balancing, and Networking > The Kubernetes network model  
Original saved excerpt offsets: [845, 1291)  
Snippet cut or saved source already truncated: True

```text
On Windows, this rule does not apply to host-network pods.
  - Agents on a node (such as system daemons, or kubelet) can communicate with all pods on that node.
- The [Service](https://kubernetes.io/docs/concepts/services-networking/service/) API lets you provide a stable (long lived) IP address or hostname for a service implemented by one or more backend pods, where the individual pods making up the service can change over time.
- Kubernetes
```

### E2 — net-002-sec-009-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/services-networking/service/  
Heading: Service > Defining a Service > Services without selectors > Note:  
Original saved excerpt offsets: [174, 401)  
Snippet cut or saved source already truncated: False

```text
The endpoint IP addresses cannot be the cluster IPs of other Kubernetes Services,
because [kube-proxy](https://kubernetes.io/docs/reference/command-line-tools-reference/kube-proxy/) doesn't support virtual IPs
as a destination.
```

### E3 — net-001-sec-002-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/services-networking/  
Heading: Services, Load Balancing, and Networking > The Kubernetes network model  
Original saved excerpt offsets: [33, 93)  
Snippet cut or saved source already truncated: True

```text
The Kubernetes network model is built out of several pieces:
```

### E4 — net-007-sec-001-ch-001 (retrieval rank 4)

Source: https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/  
Heading: DNS for Services and Pods  
Original saved excerpt offsets: [29, 158)  
Snippet cut or saved source already truncated: False

```text
Kubernetes creates DNS records for Services and Pods. You can contact
Services with consistent DNS names instead of IP addresses.
```

### E5 — net-002-sec-009-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/services-networking/service/  
Heading: Service > Defining a Service > Services without selectors > Note:  
Original saved excerpt offsets: [1114, 1245)  
Snippet cut or saved source already truncated: False

```text
You should
avoid using the reserved value `"controller"`, which identifies EndpointSlices
managed by Kubernetes' own control plane.
```

### E6 — net-007-sec-001-ch-001 (retrieval rank 4)

Source: https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/  
Heading: DNS for Services and Pods  
Original saved excerpt offsets: [160, 347)  
Snippet cut or saved source already truncated: False

```text
Kubernetes publishes information about Pods and Services which is used
to program DNS. kubelet configures Pods' DNS so that running containers
can look up Services by name rather than IP.
```

---

## k8s-096

**Question:** A CSI driver exposes administrator-only storage parameters through inline ephemeral-volume `volumeAttributes`, letting ordinary Pod authors supply them. Why is that unsafe, and what two controls can a cluster administrator use?

### E1 — stor-005-sec-005-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/storage/ephemeral-volumes/  
Heading: Ephemeral Volumes > CSI driver restrictions  
Original saved excerpt offsets: [29, 434)  
Snippet cut or saved source already truncated: False

```text
CSI ephemeral volumes allow users to provide `volumeAttributes`
directly to the CSI driver as part of the Pod spec. A CSI driver
allowing `volumeAttributes` that are typically restricted to
administrators is NOT suitable for use in an inline ephemeral volume.
For example, parameters that are normally defined in the StorageClass
should not be exposed to users through the use of inline ephemeral volumes.
```

### E2 — sec-002-sec-007-ch-001 (retrieval rank 4)

Source: https://kubernetes.io/docs/concepts/security/pod-security-standards/  
Heading: Pod Security Standards > Profile Details > Restricted > Note:  
Original saved excerpt offsets: [685, 1134)  
Snippet cut or saved source already truncated: True

```text
*[This is Linux only policy](https://kubernetes.io/docs/concepts/security/pod-security-standards/#os-specific-policy-controls) in v1.25+ `(spec.os.name != windows)`***Restricted Fields**`spec.containers[*].securityContext.allowPrivilegeEscalation``spec.initContainers[*].securityContext.allowPrivilegeEscalation``spec.ephemeralContainers[*].securityContext.allowPrivilegeEscalation`**Allowed Values**`false` |
| Running as Non-root | Containers must
```

### E3 — stor-005-sec-005-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/storage/ephemeral-volumes/  
Heading: Ephemeral Volumes > CSI driver restrictions  
Original saved excerpt offsets: [575, 783)  
Snippet cut or saved source already truncated: False

```text
- Removing Ephemeral from volumeLifecycleModes in the CSIDriver spec, which prevents the driver from being used as an inline ephemeral volume.
- Using an admission webhook to restrict how this driver is used.
```

### E4 — stor-005-sec-004-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/storage/ephemeral-volumes/  
Heading: Ephemeral Volumes > CSI ephemeral volumes > Note:  
Original saved excerpt offsets: [1203, 1408)  
Snippet cut or saved source already truncated: False

```text
The `volumeAttributes` determine what volume is prepared by the
driver. These attributes are specific to each driver and not
standardized. See the documentation of each CSI driver for further
instructions.
```

### E5 — stor-002-sec-048-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/storage/volumes/  
Heading: Volumes > Out-of-tree volume plugins > csi > Note:  
Original saved excerpt offsets: [1058, 1282)  
Snippet cut or saved source already truncated: True

```text
The value is passed as volume_id in all calls to the CSI volume driver when referencing the volume.
- readOnly : An optional boolean value indicating whether the volume is to be "ControllerPublished" (attached) as read-only.
```

### E6 — stor-005-sec-004-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/storage/ephemeral-volumes/  
Heading: Ephemeral Volumes > CSI ephemeral volumes > Note:  
Original saved excerpt offsets: [12, 255)  
Snippet cut or saved source already truncated: False

```text
Conceptually, CSI ephemeral volumes are similar to `configMap`,
`downwardAPI` and `secret` volume types: the storage is managed locally on each
node and is created together with other local resources after a Pod has been
scheduled onto a node.
```

---

## k8s-097

**Question:** How does Kubernetes garbage collection behave differently when deleting a ReplicaSet with its dependent Pods versus deleting or scaling a StatefulSet whose PVC retention policy is configured?

### E1 — work-010-sec-012-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/workloads/controllers/replicaset/  
Heading: ReplicaSet > Working with ReplicaSets > Deleting a ReplicaSet and its Pods  
Original saved excerpt offsets: [40, 341)  
Snippet cut or saved source already truncated: False

```text
To delete a ReplicaSet and all of its Pods, use
[`kubectl delete`](https://kubernetes.io/docs/reference/generated/kubectl/kubectl-commands#delete). The
[Garbage collector](https://kubernetes.io/docs/concepts/architecture/garbage-collection/) automatically deletes all of
the dependent Pods by default.
```

### E2 — work-011-sec-038-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/  
Heading: StatefulSets > PersistentVolumeClaim retention  
Original saved excerpt offsets: [583, 856)  
Snippet cut or saved source already truncated: True

```text
**`whenDeleted`**
: Configures the volume retention behavior that applies when the StatefulSet is deleted.
**`whenScaled`**
: Configures the volume retention behavior that applies when the replica count of
the StatefulSet is reduced; for example, when scaling down the set.
```

### E3 — work-011-sec-038-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/  
Heading: StatefulSets > PersistentVolumeClaim retention  
Original saved excerpt offsets: [157, 581)  
Snippet cut or saved source already truncated: True

```text
The optional `.spec.persistentVolumeClaimRetentionPolicy` field controls if
and how PVCs are deleted during the lifecycle of a StatefulSet. You must enable the
`StatefulSetAutoDeletePVC` [feature gate](https://kubernetes.io/docs/reference/command-line-tools-reference/feature-gates/)
on the API server and the controller manager to use this field.
Once enabled, there are two policies you can configure for each StatefulSet:
```

### E4 — work-011-sec-038-ch-002 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/  
Heading: StatefulSets > PersistentVolumeClaim retention  
Original saved excerpt offsets: [253, 657)  
Snippet cut or saved source already truncated: True

```text
The StatefulSet [controller](https://kubernetes.io/docs/concepts/architecture/controller/) adds
[owner references](https://kubernetes.io/docs/concepts/overview/working-with-objects/owners-dependents/#owner-references-in-object-specifications)
to its PVCs, which are then deleted by the [garbage collector](https://kubernetes.io/docs/concepts/architecture/garbage-collection/) after the Pod is terminated.
```

### E5 — work-011-sec-038-ch-002 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/  
Heading: StatefulSets > PersistentVolumeClaim retention  
Original saved excerpt offsets: [1223, 1320)  
Snippet cut or saved source already truncated: True

```text
Any StatefulSet Pod
whose id greater than the replica count is condemned and marked for deletion.
```

### E6 — work-011-sec-039-ch-001 (retrieval rank 4)

Source: https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/  
Heading: StatefulSets > PersistentVolumeClaim retention > Replicas  
Original saved excerpt offsets: [114, 415)  
Snippet cut or saved source already truncated: False

```text
Should you manually scale a StatefulSet, via `kubectl scale statefulset statefulset --replicas=X`, and then you update that StatefulSet
based on a manifest (for example: by running `kubectl apply -f statefulset.yaml`), then applying that manifest overwrites the manual scaling
that you previously did.
```

---

## k8s-098

**Question:** You are designing a new cluster that needs cluster-wide DNS, container metrics, centralized container logs, and resource-aware Pod placement. Which needs are Kubernetes addons, and which core control-plane component uses Node capacity to place Pods?

### E1 — net-002-sec-044-ch-001 (retrieval rank 4)

Source: https://kubernetes.io/docs/concepts/services-networking/service/  
Heading: Service > Discovering services > DNS  
Original saved excerpt offsets: [181, 446)  
Snippet cut or saved source already truncated: False

```text
A cluster-aware DNS server, such as CoreDNS, watches the Kubernetes API for new
Services and creates a set of DNS records for each one. If DNS has been enabled
throughout your cluster then all Pods should automatically be able to resolve
Services by their DNS name.
```

### E2 — arch-001-sec-005-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/overview/components/  
Heading: Kubernetes Components > Addons  
Original saved excerpt offsets: [332, 496)  
Snippet cut or saved source already truncated: False

```text
**[Container Resource Monitoring](https://kubernetes.io/docs/concepts/architecture/#container-resource-monitoring)**
: For collecting and storing container metrics.
```

### E3 — net-002-sec-044-ch-001 (retrieval rank 4)

Source: https://kubernetes.io/docs/concepts/services-networking/service/  
Heading: Service > Discovering services > DNS  
Original saved excerpt offsets: [448, 778)  
Snippet cut or saved source already truncated: False

```text
For example, if you have a Service called `my-service` in a Kubernetes
namespace `my-ns`, the control plane and the DNS Service acting together
create a DNS record for `my-service.my-ns`. Pods in the `my-ns` namespace
should be able to find the service by doing a name lookup for `my-service`
(`my-service.my-ns` would also work).
```

### E4 — arch-001-sec-003-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/overview/components/  
Heading: Kubernetes Components > Core Components > Control Plane Components  
Original saved excerpt offsets: [72, 224)  
Snippet cut or saved source already truncated: False

```text
**[kube-apiserver](https://kubernetes.io/docs/concepts/architecture/#kube-apiserver)**
: The core component server that exposes the Kubernetes HTTP API.
```

### E5 — arch-001-sec-005-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/overview/components/  
Heading: Kubernetes Components > Addons  
Original saved excerpt offsets: [497, 649)  
Snippet cut or saved source already truncated: False

```text
**[Cluster-level Logging](https://kubernetes.io/docs/concepts/architecture/#cluster-level-logging)**
: For saving container logs to a central log store.
```

### E6 — net-001-sec-002-ch-002 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/services-networking/  
Heading: Services, Load Balancing, and Networking > The Kubernetes network model  
Original saved excerpt offsets: [1043, 1378)  
Snippet cut or saved source already truncated: True

```text
- Pod network namespace setup is handled by system-level software implementing the [Container Runtime Interface](https://kubernetes.io/docs/concepts/containers/cri/).
- The pod network itself is managed by a [pod network implementation](https://kubernetes.io/docs/concepts/cluster-administration/addons/#networking-and-network-policy).
```

---

## k8s-099

**Question:** A developer needs to configure a Pod from a ConfigMap, later update that configuration, review Secret-management guidance, and then learn about assigning CPU and memory resources. Which documentation paths in the supplied Configuration section address those tasks, and what namespace rule applies to the Pod's ConfigMap?

### E1 — stor-002-sec-005-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/storage/volumes/  
Heading: Volumes > Types of volumes > configMap  
Original saved excerpt offsets: [15, 313)  
Snippet cut or saved source already truncated: False

```text
A [ConfigMap](https://kubernetes.io/docs/tasks/configure-pod-container/configure-pod-configmap/)
provides a way to inject configuration data into Pods.
The data stored in a ConfigMap can be referenced in a volume of type
`configMap` and then consumed by containerized applications running in a Pod.
```

### E2 — conf-002-sec-006-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/configuration/configmap/  
Heading: ConfigMaps > ConfigMaps and Pods  
Original saved excerpt offsets: [24, 294)  
Snippet cut or saved source already truncated: False

```text
You can write a Pod `spec` that refers to a ConfigMap and configures the container(s)
in that Pod based on the data in the ConfigMap. The Pod and the ConfigMap must be in
the same [namespace](https://kubernetes.io/docs/concepts/overview/working-with-objects/namespaces).
```

### E3 — conf-002-sec-007-ch-001 (retrieval rank 4)

Source: https://kubernetes.io/docs/concepts/configuration/configmap/  
Heading: ConfigMaps > ConfigMaps and Pods > Note:  
Original saved excerpt offsets: [575, 672)  
Snippet cut or saved source already truncated: True

```text
There are four different ways that you can use a ConfigMap to configure
a container inside a Pod:
```

### E4 — stor-002-sec-005-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/storage/volumes/  
Heading: Volumes > Types of volumes > configMap  
Original saved excerpt offsets: [315, 579)  
Snippet cut or saved source already truncated: False

```text
When referencing a ConfigMap, you provide the name of the ConfigMap in the
volume. You can customize the path to use for a specific
entry in the ConfigMap. The following configuration shows how to mount
the `log-config` ConfigMap onto a Pod called `configmap-pod`:
```

### E5 — conf-001-sec-003-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/configuration/  
Heading: Configuration > Kubernetes configuration-related APIs > ConfigMaps  
Original saved excerpt offsets: [16, 328)  
Snippet cut or saved source already truncated: False

```text
A ConfigMap is an API object used to store non-confidential data in key-value pairs.
[Pods](https://kubernetes.io/docs/concepts/workloads/pods/) can consume ConfigMaps as
environment variables, command-line arguments, or as configuration files in a
[volume](https://kubernetes.io/docs/concepts/storage/volumes/).
```

### E6 — conf-001-sec-003-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/configuration/  
Heading: Configuration > Kubernetes configuration-related APIs > ConfigMaps  
Original saved excerpt offsets: [330, 544)  
Snippet cut or saved source already truncated: False

```text
A ConfigMap allows you to decouple environment-specific configuration from your [container images](https://kubernetes.io/docs/reference/glossary/?all=true#term-image), so that your applications are easily portable.
```

---

## k8s-100

**Question:** How can Kubernetes both spread replicas across topology domains such as zones and let each scheduled Pod discover the zone and region it actually landed in?

### E1 — stor-007-sec-006-ch-001 (retrieval rank 3)

Source: https://kubernetes.io/docs/concepts/storage/dynamic-provisioning/  
Heading: Dynamic Volume Provisioning > Topology Awareness  
Original saved excerpt offsets: [23, 393)  
Snippet cut or saved source already truncated: False

```text
In [Multi-Zone](https://kubernetes.io/docs/setup/best-practices/multiple-zones/) clusters, Pods can be spread across
Zones in a Region. Single-Zone storage backends should be provisioned in the Zones where
Pods are scheduled. This can be accomplished by setting the
[Volume Binding Mode](https://kubernetes.io/docs/concepts/storage/storage-classes/#volume-binding-mode).
```

### E2 — sched-003-sec-031-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/  
Heading: Assigning Pods to Nodes > Pod topology spread constraints  
Original saved excerpt offsets: [36, 378)  
Snippet cut or saved source already truncated: False

```text
You can use *topology spread constraints* to control how [Pods](https://kubernetes.io/docs/concepts/workloads/pods/)
are spread across your cluster among failure-domains such as regions, zones, nodes, or among any other
topology domains that you define. You might do this to improve performance, expected availability, or
overall utilization.
```

### E3 — sched-004-sec-001-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/scheduling-eviction/topology-spread-constraints/  
Heading: Pod Topology Spread Constraints  
Original saved excerpt offsets: [35, 362)  
Snippet cut or saved source already truncated: False

```text
You can use *topology spread constraints* to control how
[Pods](https://kubernetes.io/docs/concepts/workloads/pods/) are spread across your cluster
among failure-domains such as regions, zones, nodes, and other user-defined topology
domains. This can help to achieve high availability as well as efficient resource
utilization.
```

### E4 — sched-004-sec-008-ch-001 (retrieval rank 4)

Source: https://kubernetes.io/docs/concepts/scheduling-eviction/topology-spread-constraints/  
Heading: Pod Topology Spread Constraints > Consistency  
Original saved excerpt offsets: [412, 719)  
Snippet cut or saved source already truncated: False

```text
You need a mechanism to ensure that all the nodes in a topology domain (such as a
cloud provider region) are labeled consistently.
To avoid you needing to manually label nodes, most clusters automatically
populate well-known labels such as `kubernetes.io/hostname`. Check whether
your cluster supports this.
```

### E5 — sched-003-sec-031-ch-001 (retrieval rank 1)

Source: https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/  
Heading: Assigning Pods to Nodes > Pod topology spread constraints  
Original saved excerpt offsets: [380, 540)  
Snippet cut or saved source already truncated: False

```text
Read [Pod topology spread constraints](https://kubernetes.io/docs/concepts/scheduling-eviction/topology-spread-constraints/)
to learn more about how these work.
```

### E6 — sched-004-sec-001-ch-001 (retrieval rank 2)

Source: https://kubernetes.io/docs/concepts/scheduling-eviction/topology-spread-constraints/  
Heading: Pod Topology Spread Constraints  
Original saved excerpt offsets: [364, 604)  
Snippet cut or saved source already truncated: False

```text
You can set [cluster-level constraints](https://kubernetes.io/docs/concepts/scheduling-eviction/topology-spread-constraints/#cluster-level-default-constraints) as a default,
or configure topology spread constraints for individual workloads.
```

---
