
__author__ = "Cristiana L. Lara"
# Nested Decomposition description at:
# http://www.optimization-online.org/DB_FILE/2017/08/6162.pdf

import time
start_time = time.time()
from GTEPblock_SDDP_test import *
elapsed_time = time.time() - start_time
print('CPU time to generate the scenario tree and blocks (s):', elapsed_time)

########################### Decomposition Parameters ###########################
m.ngo_rn_par = Param(m.rn_r, m.n_stage, default=0, initialize=0, mutable=True)
m.ngo_th_par = Param(m.th_r, m.n_stage, default=0, initialize=0, mutable=True)
m.ngb_rn_par = Param(m.rn_r, m.n_stage, default=0, initialize=0, mutable=True)
m.ngb_th_par = Param(m.th_r, m.n_stage, default=0, initialize=0, mutable=True)
m.ngo_rn_par_k = Param(m.rn_r, m.n_stage, m.iter, default=0, initialize=0, mutable=True)
m.ngo_th_par_k = Param(m.th_r, m.n_stage, m.iter, default=0, initialize=0, mutable=True)
m.ngb_rn_par_k = Param(m.rn_r, m.n_stage, m.iter, default=0, initialize=0, mutable=True)
m.ngb_th_par_k = Param(m.th_r, m.n_stage, m.iter, default=0, initialize=0, mutable=True)
m.cost=Param(m.n_stage,m.iter, default=0, initialize=0, mutable=True)
m.mltp_o_rn=Param(m.rn_r,m.n_stage, m.iter, default=0, initialize=0, mutable=True)
m.mltp_o_th=Param(m.th_r,m.n_stage,m.iter, default=0, initialize=0, mutable=True)
m.mltp_b_rn=Param(m.rn_r,m.n_stage,m.iter, default=0, initialize=0, mutable=True)
m.mltp_b_th=Param(m.th_r,m.n_stage,m.iter, default=0, initialize=0, mutable=True)
m.cost_t=Param(m.n_stage,m.iter, default=0, initialize=0, mutable=True)

#Parameters to compute upper and lower bounds
m.cost_forward=Param(m.iter, default=0, initialize=0, mutable=True)
m.cost_UB=Param(m.iter, default=0, initialize=0, mutable=True)
m.cost_LB=Param(m.iter, default=0, initialize=0, mutable=True)
m.gap=Param(m.iter, default=0, initialize=0, mutable=True)

#Retrive duals
for t in m.t:
    for n in N_stage[t]:
        m.Bl[t,n].dual = Suffix(direction=Suffix.IMPORT)

#Stochastic Dual Dynamic integer Programming Algorithm (SDDiP)
for iter_ in m.iter:

    #Forward Pass##############################################################

    for t in m.t:
        for n in N_stage[t]:
            print ("Time period", t)
            print ("Current Node", n)

            #Fix alphafut=0 for iter 1
            if iter_ == 1:
                m.Bl[t,n].alphafut.fix(0)

            #add equality linking with parental nodes for stages =/= 1
            if iter_ == 1:
                if t != 1:
                    for (rn,r) in m.rn_r:
                        for pn in N_stage[t-1]:
                            if pn in PN[n]:
                                m.Bl[t,n].link_equal1.add(expr=(m.Bl[t,n].ngo_rn_prev[rn,r] \
                                == m.ngo_rn_par[rn,r,t-1,pn]))
                                if t > LT[rn]:
                                    m.Bl[t,n].link_equal3.add(expr=(m.Bl[t,n].ngb_rn_LT[rn,r] \
                                    ==  m.ngb_rn_par[rn,r,t-m.LT[rn],pn]))
                    for (th,r) in m.th_r:
                        for pn in N_stage[t-1]:
                            if pn in PN[n]:
                                m.Bl[t,n].link_equal2.add(expr=(m.Bl[t,n].ngo_th_prev[th,r] \
                                ==  m.ngo_th_par[th,r,t-1,pn]))
                                if  t > LT[th]:
                                    m.Bl[t,n].link_equal4.add(expr=(m.Bl[t,n].ngb_th_LT[th,r] \
                                    ==  m.ngo_th_par[th,r,t-m.LT[th],pn]))

            #Solve the model
            mipsolver = SolverFactory('gurobi')#_persistent')
#                mipsolver.set_instance(m.Bl[t,n,pn])
            mipsolver.options['mipgap']=0.0001
            mipsolver.options['timelimit']=40
            mipsolver.options['threads']=6
            results = mipsolver.solve(m.Bl[t,n])#, tee=True)#,save_results=False)

            #Fix the linking variable as parameter for next t
            if t != m.t.last():
                for (rn,r) in m.rn_r:
                    m.ngo_rn_par[rn,r,t,n]=m.Bl[t,n].ngo_rn[rn,r].value
                    m.ngb_rn_par[rn,r,t,n]=m.Bl[t,n].ngb_rn[rn,r].value
                for (th,r) in m.th_r:
                    m.ngo_th_par[th,r,t,n]=m.Bl[t,n].ngo_th[th,r].value
                    m.ngb_th_par[th,r,t,n]=m.Bl[t,n].ngb_th[th,r].value

            for (rn,r) in m.rn_r:
                m.ngo_rn_par_k[rn,r,t,n,iter_]=m.Bl[t,n].ngo_rn[rn,r].value
                m.ngb_rn_par_k[rn,r,t,n,iter_]=m.Bl[t,n].ngb_rn[rn,r].value

            for (th,r) in m.th_r:
                m.ngo_th_par_k[th,r,t,n,iter_]=m.Bl[t,n].ngo_th[th,r].value
                m.ngb_th_par_k[th,r,t,n,iter_]=m.Bl[t,n].ngb_th[th,r].value

            #Store obj value to compute UB
            m.cost_t[t,n,iter_]=m.Bl[t,n].obj() - m.Bl[t,n].alphafut.value

#    m.cost_t.pprint()

    #Compute upper bound (feasible solution)
    m.cost_forward[iter_]=sum(m.prob[n]*m.cost_t[t,n,iter_] for t in m.t for n in N_stage[t])
    m.cost_UB[iter_]=min(value(m.cost_forward[kk]) for kk in m.iter if kk <= iter_)
    m.cost_UB.pprint()
    m.Bl[t,n].alphafut.unfix()
    elapsed_time = time.time() - start_time
    print ("CPU Time (s)", elapsed_time)

    #Backward Pass############################################################

    m.k.add(iter_)

    for t in reversed(list(m.t)):
        for n in N_stage[t]:
            print ("Time period", t)
            print ("Current Node", n)
            if t == m.t.last():
                m.Bl[t,n].alphafut.fix(0)
            else:
                m.Bl[t,n].alphafut.unfix()

            #add Benders cut
            if t != m.t.last():
                for k in m.k:
                    # for pn_ in N_stage[t]:
                    #     if pn_ == n:
                    m.Bl[t,n].fut_cost.add(expr=(m.Bl[t,n].alphafut \
                    >= sum((m.prob[n_]/m.prob[n])*m.cost[t+1,n_,k]\
                            for n_ in N_stage[t+1] if n in PN[n_])
                        + sum((m.prob[n_]/m.prob[n])*m.mltp_o_rn[rn,r,t+1,n_,k]* \
                            (m.ngo_rn_par_k[rn,r,t,n,k] - m.Bl[t,n].ngo_rn[rn,r]) \
                            for rn,r in m.rn_r for n_ in N_stage[t+1] if n in PN[n_])\
                        + sum((m.prob[n_]/m.prob[n])*m.mltp_o_th[th,r,t+1,n_,k]* \
                            (m.ngo_th_par_k[th,r,t,n,k] - m.Bl[t,n].ngo_th[th,r]) \
                            for th,r in m.th_r for n_ in N_stage[t+1] if n in PN[n_])\
                        + sum((m.prob[n_]/m.prob[n])*m.mltp_b_rn[rn,r,t+m.LT[rn],n_,k]* \
                            (m.ngb_rn_par_k[rn,r,t,n,k] - m.Bl[t,n].ngb_rn[rn,r]) \
                            for rn,r in m.rn_r for n_ in N_stage[t+1] if n in PN[n_] \
                            and (t+m.LT[rn] <= m.t.last()))\
                        + sum((m.prob[n_]/m.prob[n])*m.mltp_b_th[th,r,t+m.LT[th],n_,k]* \
                            (m.ngb_th_par_k[th,r,t,n,k] - m.Bl[t,n].ngb_th[th,r]) \
                            for th,r in m.th_r for n_ in N_stage[t+1] if n in PN[n_]\
                            and (t+m.LT[th] <= m.t.last()))
                        ))
#                m.Bl[t,n,pn].fut_cost.pprint()

            #Solve the model
            #opt = SolverFactory('cplex')
            opt = SolverFactory('gurobi')
            #opt.set_instance(m.Bl[t])
            opt.options['relax_integrality']=1
            opt.options['threads']=6
            #opt.options['SolutionNumber']=0
            results = opt.solve(m.Bl[t,n])#, tee=True)#, save_results=False)#
#                m.Bl[t,n,pn].alphafut.pprint()

            #Get Lagrange multiplier from linking equality
            if t != m.t.first():
                for rn_r_index in range(len(rn_r)):
                    i = rn_r[rn_r_index][0]
                    j = rn_r[rn_r_index][1]
                    m.mltp_o_rn[i,j,t,n,iter_]= - m.Bl[t,n].dual[m.Bl[t,n].link_equal1[rn_r_index+1]]
                    if t > m.LT[rn]:
                        m.mltp_b_rn[i,j,t,n,iter_]= - m.Bl[t,n].dual[m.Bl[t,n].link_equal3[rn_r_index+1]]
                    else:
                        m.mltp_b_rn[i,j,t,n,iter_]=0


            if t != m.t.first():
                for th_r_index in range(len(th_r)):
                    i = th_r[th_r_index][0]
                    j = th_r[th_r_index][1]
                    m.mltp_o_th[i,j,t,n,iter_]= - m.Bl[t,n].dual[m.Bl[t,n].link_equal2[th_r_index+1]]
                    if t > m.LT[th]:
                        m.mltp_b_th[i,j,t,n,iter_]= - m.Bl[t,n].dual[m.Bl[t,n].link_equal4[th_r_index+1]]
                    else:
                        m.mltp_b_th[i,j,t,n,iter_]=0
#                m.mltp_o_th.pprint()

            #Get optimal value
            m.cost[t,n,iter_]=m.Bl[t,n].obj()


    #Compute lower bound
    m.cost_LB[iter_]=m.cost[1,'O',iter_]
    m.cost_LB.pprint()
    #Compute optimality gap
    m.gap[iter_]=(m.cost_UB[iter_]-m.cost_LB[iter_])/m.cost_UB[iter_]*100
    print (m.gap[iter_].value)

    if value(m.gap[iter_]) <= 1:
        break

    elapsed_time = time.time() - start_time
    print ("CPU Time (s)", elapsed_time)

elapsed_time = time.time() - start_time

print ("Upper Bound", m.cost_UB[iter_].value)
print ("Lower Bound", m.cost_LB[iter_].value)
print ("Optimality gap (%)", m.gap[iter_].value)
print ("CPU Time (s)", elapsed_time)

#post_process()